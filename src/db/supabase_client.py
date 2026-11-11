"""
Cliente de Conexão com o Banco de Dados (PostgreSQL / Supabase)
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
Responsável: Maria Eduarda (DevOps & Backend)
Issue #41 | Referência: GUIA_OFICIAL_PROJETO.md

Implementa acesso resiliente ao PostgreSQL (Supabase na nuvem / Docker) via psycopg
com suporte completo às correções da revisão do PR #50 e preservando 100% das regras de negócio:
1. Conexão real com PostgreSQL via psycopg usando DATABASE_URL (sob demanda/lazy).
2. schema.sql como fonte única da verdade para a estrutura de 9 tabelas normalizadas.
3. RLS (Row Level Security) e sigilo orçamentário (RNF-01 e RNF-02): cabe_no_orcamento() booleano.
4. Precisão monetária absoluta com Decimal (sem floats nos cálculos financeiros e Pix).
5. Timestamps e janelas com ponto de partida amarrado por janela de horário.
6. Rateio individualizado pós-rolê (despesa_rateios) com quitação por participante.
   Nota de escopo (Issue #45): A criptografia da chave Pix em repouso (pgcrypto/Vault)
   será implementada na entrega da Tela 4 / Finanças.
7. Identificação, segurança e LGPD: token_hash, token_organizador_hash e apagar_salas_expiradas().
8. Interface RepositorioSupabase que persiste e reconstrói o objeto Sala completo (src/salas/modelos.py).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Union
import uuid

from src.interpretador.campos import PerfilInterpretado, Preferencias
from src.interpretador.tempo import JanelaResolvida
from src.salas.janelas import JanelaComum
from src.salas.modelos import COLETANDO, Participante, Resultado, Sala, Sugestao
from src.state import Repositorio

# Tenta importar psycopg para PostgreSQL real
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_DISPONIVEL = True
except ImportError:
    PSYCOPG_DISPONIVEL = False

# Tenta importar httpx para checar endpoint REST do Supabase
try:
    import httpx
    HTTPX_DISPONIVEL = True
except ImportError:
    HTTPX_DISPONIVEL = False

# Caminhos padrão e fuso de Brasília (America/Sao_Paulo)
SCHEMA_SQL_PATH = Path(__file__).parent / "schema.sql"
LOCAL_DB_PATH = Path("data/app_local.db")
FUSO_BRASILIA = timezone(timedelta(hours=-3))


def _carregar_env() -> None:
    """Carrega variáveis do .env para os.environ caso ainda não estejam definidas."""
    caminhos = [
        Path(".env"),
        Path("/app/.env"),
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for p in caminhos:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass


_carregar_env()


def quantizar_decimal(valor: Union[Decimal, str, float, int, None]) -> Decimal:
    """Garante duas casas decimais exatas usando Decimal."""
    if valor is None:
        return Decimal("0.00")
    if isinstance(valor, Decimal):
        return valor.quantize(Decimal("0.01"))
    return Decimal(str(valor)).quantize(Decimal("0.01"))


def _uuid_deterministico(prefixo: str, sala_id: str, identificador: str) -> str:
    """Converte um ID curto de domínio (ex: token_hex de 12 chars ou letra 'A') em UUID válido."""
    try:
        return str(uuid.UUID(str(identificador)))
    except (ValueError, TypeError):
        return str(uuid.uuid5(uuid.NAMESPACE_OID, f"{prefixo}:{sala_id}:{identificador}"))


def _iso_com_fuso(dt: Union[datetime, str, None]) -> Optional[str]:
    """Serializa datetime para ISO-8601 preservando o fuso de Brasília (-03:00) quando naive."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=FUSO_BRASILIA).isoformat()
    return dt.isoformat()


def _para_datetime_local(valor: Union[datetime, str, None]) -> datetime:
    """Converte timestamp do banco (TIMESTAMPTZ ou texto ISO) para datetime local naive (America/Sao_Paulo)."""
    if valor is None:
        return datetime.now(FUSO_BRASILIA).replace(tzinfo=None)
    if isinstance(valor, datetime):
        if valor.tzinfo is not None:
            return valor.astimezone(FUSO_BRASILIA).replace(tzinfo=None)
        return valor
    texto = str(valor).strip()
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is not None:
            return dt.astimezone(FUSO_BRASILIA).replace(tzinfo=None)
        return dt
    except ValueError:
        return datetime.now(FUSO_BRASILIA).replace(tzinfo=None)


def _decodificar_json(valor: Any, padrao: Any) -> Any:
    """Decodifica coluna JSONB (já dict/list no psycopg) ou TEXT (string JSON no SQLite)."""
    if valor is None:
        return padrao
    if isinstance(valor, (dict, list)):
        return valor
    if isinstance(valor, str):
        try:
            return json.loads(valor)
        except Exception:
            return padrao
    return padrao


class SupabaseClient:
    """
    Cliente de banco de dados do Orquestrador de Rolês.
    Opera com PostgreSQL nativo (psycopg) quando DATABASE_URL estiver configurada.
    O fallback em SQLite só é permitido em ambiente de teste ou desenvolvimento local.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        use_memory_fallback: bool = False,
        db_path: Optional[Path] = None,
    ):
        self.database_url = database_url if database_url is not None else os.environ.get("DATABASE_URL")
        self.use_memory = use_memory_fallback
        self.db_path = db_path or LOCAL_DB_PATH
        self._explicit_fallback = bool(use_memory_fallback or db_path is not None)

        # Se solicitou explicitamente memória ou db_path isolado para teste unitário, usa SQLite
        if self._explicit_fallback and database_url is None:
            self.is_postgres = False
        else:
            self.is_postgres = bool(self.database_url and PSYCOPG_DISPONIVEL)

        if not self.is_postgres and not self._explicit_fallback:
            ambiente = os.environ.get("ENVIRONMENT", "desenvolvimento").strip().lower()
            if ambiente in ("producao", "production"):
                raise RuntimeError(
                    "DATABASE_URL do PostgreSQL/Supabase é obrigatória em ambiente de produção "
                    "(ENVIRONMENT=producao). Fallback SQLite desativado em produção."
                )

        self._conn = None
        self._schema_inicializado = False

    def _get_connection(self):
        """Retorna uma conexão ativa (conexão lazy, sob demanda)."""
        if self.is_postgres:
            if self._conn is None or self._conn.closed:
                self._conn = psycopg.connect(self.database_url, row_factory=dict_row)
                self._conn.autocommit = True
            return self._conn
        else:
            if self.use_memory:
                if self._conn is None:
                    self._conn = sqlite3.connect(":memory:", check_same_thread=False)
                    self._conn.row_factory = sqlite3.Row
                    self._conn.execute("PRAGMA foreign_keys = ON;")
                return self._conn
            else:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                if self._conn is None:
                    self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                    self._conn.row_factory = sqlite3.Row
                    self._conn.execute("PRAGMA foreign_keys = ON;")
                return self._conn

    def garantir_schema(self) -> None:
        """Aplica o schema.sql como fonte única da verdade."""
        if self._schema_inicializado:
            return

        if not SCHEMA_SQL_PATH.exists():
            return

        sql_content = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
        conn = self._get_connection()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(sql_content)
        else:
            sqlite_sql = self._adaptar_sql_para_sqlite(sql_content)
            cur = conn.cursor()
            cur.executescript(sqlite_sql)
            conn.commit()

        self._schema_inicializado = True

    @staticmethod
    def _adaptar_sql_para_sqlite(sql: str) -> str:
        """Converte comandos específicos do Postgres para execução limpa no SQLite de teste/dev."""
        linhas = []
        ignorar_bloco_do = False

        for linha in sql.splitlines():
            if "CREATE EXTENSION" in linha:
                continue
            if "DO $$" in linha:
                ignorar_bloco_do = True
                continue
            if ignorar_bloco_do:
                if "$$;" in linha:
                    ignorar_bloco_do = False
                continue
            if "ENABLE ROW LEVEL SECURITY" in linha:
                continue

            l = linha
            l = re.sub(r"UUID PRIMARY KEY DEFAULT uuid_generate_v4\(\)", "TEXT PRIMARY KEY", l)
            l = re.sub(r"\bUUID\b", "TEXT", l)
            l = re.sub(r"\bTIMESTAMPTZ\b", "TEXT", l)
            l = re.sub(r"\bJSONB\b", "TEXT", l)
            l = re.sub(r"DEFAULT \(NOW\(\) \+ INTERVAL '30 days'\)", "DEFAULT (datetime('now', '+30 days'))", l)
            l = re.sub(r"DEFAULT NOW\(\)", "DEFAULT CURRENT_TIMESTAMP", l)
            l = re.sub(r"CHECK \(maior_18_anos IS TRUE\)", "CHECK (maior_18_anos = 1)", l)

            linhas.append(l)

        return "\n".join(linhas)

    def fechar(self) -> None:
        """Fecha a conexão ativa com o banco."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ==========================================================================
    # VERIFICAÇÃO DE CONECTIVIDADE
    # ==========================================================================
    def checar_conexao(self) -> Dict[str, Any]:
        """Testa conectividade com o banco de dados (PostgreSQL ou SQLite de teste/dev)."""
        self.garantir_schema()
        conn = self._get_connection()
        try:
            if self.is_postgres:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 as teste;")
                    res = cur.fetchone()
                return {"conectado": True, "tipo": "PostgreSQL", "resultado": res["teste"]}
            else:
                cur = conn.cursor()
                cur.execute("SELECT 1 as teste;")
                res = cur.fetchone()
                return {"conectado": True, "tipo": "SQLite", "resultado": res["teste"]}
        except Exception as e:
            return {"conectado": False, "erro": str(e)}

    # ==========================================================================
    # GESTÃO DE SALAS (ROLE-XXXX) & EXPIRAÇÃO LGPD
    # ==========================================================================
    def criar_sala(
        self,
        codigo_sala: str,
        nome_role: str,
        organizador_nome: Optional[str] = None,
        criador_nome: Optional[str] = None,
        token_organizador_hash: Optional[str] = None,
        criador_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cria uma sala de rolê no formato ROLE-XXXX com token de organizador."""
        self.garantir_schema()
        conn = self._get_connection()
        sala_id = str(uuid.uuid4())
        nome_org = organizador_nome or criador_nome or "Organizador"
        token_hash = token_organizador_hash or f"tok_{uuid.uuid4().hex[:16]}"
        agora = datetime.now(timezone.utc).isoformat()
        expira_em = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO salas (id, codigo_sala, nome_role, organizador_nome, token_organizador_hash, criador_id, status, expira_em, criado_em, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, 'coletando', %s, %s, %s)
                    RETURNING id, codigo_sala, nome_role, organizador_nome, status;
                    """,
                    (sala_id, codigo_sala, nome_role, nome_org, token_hash, criador_id, expira_em, agora, agora),
                )
                return cur.fetchone()
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO salas (id, codigo_sala, nome_role, organizador_nome, token_organizador_hash, criador_id, status, expira_em, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, 'coletando', ?, ?, ?);
                """,
                (sala_id, codigo_sala, nome_role, nome_org, token_hash, criador_id, expira_em, agora, agora),
            )
            conn.commit()
            return {
                "id": sala_id,
                "codigo_sala": codigo_sala,
                "nome_role": nome_role,
                "organizador_nome": nome_org,
                "status": "coletando",
            }

    def obter_sala(self, codigo_sala: str) -> Optional[Dict[str, Any]]:
        """Busca os dados brutos da linha da tabela `salas` pelo código único ROLE-XXXX."""
        self.garantir_schema()
        conn = self._get_connection()
        codigo = (codigo_sala or "").strip().upper()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM salas WHERE codigo_sala = %s;", (codigo,))
                row = cur.fetchone()
                return dict(row) if row else None
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM salas WHERE codigo_sala = ?;", (codigo,))
            row = cur.fetchone()
            return dict(row) if row else None

    def apagar_salas_expiradas(self) -> int:
        """
        Remove salas cujo prazo de retenção LGPD de 30 dias (`expira_em`) já venceu (ADR 0008).
        Graças ao ON DELETE CASCADE, apaga automaticamente participantes, janelas, sugestões e votos.
        Retorna a quantidade de salas removidas.
        """
        self.garantir_schema()
        conn = self._get_connection()
        agora_iso = datetime.now(timezone.utc).isoformat()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM salas WHERE expira_em < NOW();")
                return cur.rowcount or 0
        else:
            cur = conn.cursor()
            cur.execute("DELETE FROM salas WHERE expira_em < ?;", (agora_iso,))
            removidas = cur.rowcount or 0
            conn.commit()
            return removidas

    # ==========================================================================
    # PARTICIPANTES & SIGILO ORÇAMENTÁRIO (RNF-01 / RNF-02)
    # ==========================================================================
    def adicionar_participante(
        self,
        codigo_sala: str,
        nome: str,
        *,
        limite_gasto_rs: Union[Decimal, str, int],
        janelas: List[Dict[str, Any]],
        token_hash: str,
        confirmado: bool = False,
        usuario_id: Optional[str] = None,
        vibe_hoje: Optional[str] = None,
        transporte_hoje: Optional[str] = None,
        codigo_participante: Optional[str] = None,
        perfil_json: Optional[Union[Dict[str, Any], str]] = None,
    ) -> Dict[str, Any]:
        """
        Adiciona um participante validando estritamente os campos obrigatórios (sem inventar dados).
        Argumentos após `nome` são obrigatoriamente nomeados (keyword-only).
        """
        if not nome or not str(nome).strip():
            raise ValueError("O nome do participante é obrigatório.")
        if limite_gasto_rs is None or isinstance(limite_gasto_rs, (bool, list, dict)):
            raise ValueError("O teto de gastos (limite_gasto_rs) é obrigatório.")
        try:
            teto_val = quantizar_decimal(limite_gasto_rs)
        except Exception as e:
            raise ValueError(f"Valor inválido para limite_gasto_rs: {limite_gasto_rs}") from e
        if teto_val < Decimal("0.00"):
            raise ValueError("O limite_gasto_rs não pode ser negativo.")

        if not token_hash or not str(token_hash).strip():
            raise ValueError("O hash de autenticação (token_hash) é obrigatório.")

        if not isinstance(janelas, list) or len(janelas) == 0:
            raise ValueError("É obrigatório informar pelo menos uma janela de horário em `janelas`.")

        janelas_validadas = []
        for idx, j in enumerate(janelas):
            if not isinstance(j, dict):
                raise ValueError(f"Janela na posição {idx} deve ser um dicionário.")
            inicio = j.get("inicio")
            fim = j.get("fim")
            ra = j.get("ra_origem") or j.get("regiao_ra")
            if not inicio or not fim or not ra:
                raise ValueError(
                    f"Janela na posição {idx} incompleta: 'inicio', 'fim' e 'ra_origem' são obrigatórios."
                )
            janelas_validadas.append(
                {
                    "inicio": _iso_com_fuso(inicio),
                    "fim": _iso_com_fuso(fim),
                    "disponivel": bool(j.get("disponivel", True)),
                    "ra_origem": str(ra).strip(),
                }
            )

        sala = self.obter_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala com código '{codigo_sala}' não encontrada.")

        sala_id = sala["id"]
        participante_id = str(uuid.uuid4())
        cod_part = codigo_participante or participante_id
        perfil_str = json.dumps(perfil_json, ensure_ascii=False) if isinstance(perfil_json, dict) else perfil_json
        conn = self._get_connection()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sala_participantes (
                        id, codigo_participante, sala_id, usuario_id, nome, token_hash,
                        confirmado, limite_gasto_rs, vibe_hoje, transporte_hoje, perfil_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        participante_id,
                        cod_part,
                        sala_id,
                        usuario_id,
                        nome.strip(),
                        token_hash.strip(),
                        bool(confirmado),
                        teto_val,
                        vibe_hoje,
                        transporte_hoje,
                        perfil_str,
                    ),
                )
                for j in janelas_validadas:
                    cur.execute(
                        """
                        INSERT INTO participante_janelas (id, participante_id, inicio, fim, disponivel, ra_origem)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (str(uuid.uuid4()), participante_id, j["inicio"], j["fim"], j["disponivel"], j["ra_origem"]),
                    )
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sala_participantes (
                    id, codigo_participante, sala_id, usuario_id, nome, token_hash,
                    confirmado, limite_gasto_rs, vibe_hoje, transporte_hoje, perfil_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    participante_id,
                    cod_part,
                    sala_id,
                    usuario_id,
                    nome.strip(),
                    token_hash.strip(),
                    1 if confirmado else 0,
                    str(teto_val),
                    vibe_hoje,
                    transporte_hoje,
                    perfil_str,
                ),
            )
            for j in janelas_validadas:
                cur.execute(
                    """
                    INSERT INTO participante_janelas (id, participante_id, inicio, fim, disponivel, ra_origem)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        str(uuid.uuid4()),
                        participante_id,
                        j["inicio"],
                        j["fim"],
                        1 if j["disponivel"] else 0,
                        j["ra_origem"],
                    ),
                )
            conn.commit()

        return {
            "id": participante_id,
            "codigo_participante": cod_part,
            "sala_id": sala_id,
            "nome": nome.strip(),
            "confirmado": bool(confirmado),
        }

    def listar_participantes_sala(self, codigo_sala: str, incluir_sigilo: bool = False) -> List[Dict[str, Any]]:
        """
        Lista participantes sem expor limite_gasto_rs por padrão (RNF-01 e RNF-02).
        Carrega as janelas associadas a cada participante.
        """
        sala = self.obter_sala(codigo_sala)
        if not sala:
            return []

        conn = self._get_connection()
        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, codigo_participante, sala_id, nome, confirmado, vibe_hoje, transporte_hoje, respondeu_em, limite_gasto_rs
                    FROM sala_participantes
                    WHERE sala_id = %s
                    ORDER BY respondeu_em ASC;
                    """,
                    (sala["id"],),
                )
                rows = [dict(r) for r in cur.fetchall()]
                for p in rows:
                    cur.execute(
                        "SELECT id, inicio, fim, disponivel, ra_origem as regiao_ra FROM participante_janelas WHERE participante_id = %s;",
                        (p["id"],),
                    )
                    p["janelas_disponiveis"] = [dict(j) for j in cur.fetchall()]
                    if not incluir_sigilo:
                        p.pop("limite_gasto_rs", None)
                return rows
        else:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, codigo_participante, sala_id, nome, confirmado, vibe_hoje, transporte_hoje, respondeu_em, limite_gasto_rs
                FROM sala_participantes
                WHERE sala_id = ?
                ORDER BY respondeu_em ASC;
                """,
                (sala["id"],),
            )
            rows = [dict(r) for r in cur.fetchall()]
            for p in rows:
                cur.execute(
                    "SELECT id, inicio, fim, disponivel, ra_origem as regiao_ra FROM participante_janelas WHERE participante_id = ?;",
                    (p["id"],),
                )
                p["janelas_disponiveis"] = [dict(j) for j in cur.fetchall()]
                if not incluir_sigilo:
                    p.pop("limite_gasto_rs", None)
            return rows

    def cabe_no_orcamento(
        self,
        codigo_sala: str,
        custo_por_pessoa: Union[Decimal, str, float, int],
    ) -> bool:
        """
        Verificação segura de teto orçamentário (RNF-01 e RNF-02).
        Devolve se o custo cabe no orçamento de TODOS os participantes,
        SEM revelar o orçamento individual nem o valor do menor orçamento.
        """
        min_teto = self._obter_menor_orcamento_sala(codigo_sala)
        if min_teto is None:
            return False if self.obter_sala(codigo_sala) is None else True
        custo = quantizar_decimal(custo_por_pessoa)
        return custo <= min_teto

    def _obter_menor_orcamento_sala(self, codigo_sala: str) -> Optional[Decimal]:
        """
        Método estritamente interno (privado) para cálculo de `cabe_no_orcamento` (RNF-01/02).
        Nunca deve ser exposto em rotas ou painéis públicos.
        """
        sala = self.obter_sala(codigo_sala)
        if not sala:
            return None

        conn = self._get_connection()
        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT MIN(limite_gasto_rs) as min_teto FROM sala_participantes WHERE sala_id = %s AND limite_gasto_rs IS NOT NULL;",
                    (sala["id"],),
                )
                row = cur.fetchone()
                return Decimal(str(row["min_teto"])).quantize(Decimal("0.01")) if row and row["min_teto"] is not None else None
        else:
            cur = conn.cursor()
            cur.execute(
                "SELECT MIN(CAST(limite_gasto_rs AS REAL)) as min_teto FROM sala_participantes WHERE sala_id = ? AND limite_gasto_rs IS NOT NULL;",
                (sala["id"],),
            )
            row = cur.fetchone()
            return Decimal(str(row["min_teto"])).quantize(Decimal("0.01")) if row and row["min_teto"] is not None else None

    # ==========================================================================
    # SUGESTÕES DE ROLÊ & VOTAÇÃO
    # ==========================================================================
    def adicionar_sugestao(
        self,
        codigo_sala: str,
        local_id: str,
        nome_local: str,
        regiao_ra: str,
        endereco: str,
        inicio: Union[datetime, str],
        fim: Union[datetime, str],
        horario_texto: str,
        consumo_rs: Union[Decimal, str, float, int],
        gasto_min: Union[Decimal, str, float, int],
        gasto_max: Union[Decimal, str, float, int],
        explicacao: str,
        posicao: int = 1,
        letra_card: str = "A",
        tipo: str = "bar",
        tiktok_url: Optional[str] = None,
        nota_justica: float = 0.0,
        regiao_texto: Optional[str] = None,
        horario_situacao: str = "aberto",
        contagem: str = "todos podem",
        tempo_medio_min: Optional[int] = None,
        tempo_max_min: Optional[int] = None,
        pontuacao: float = 0.0,
        fonte: str = "2fa",
        vibes: Optional[List[str]] = None,
        por_participante: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Salva um cartão de sugestão gerado pela IA com centavos exatos (Decimal)."""
        sala = self.obter_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala '{codigo_sala}' não encontrada.")

        sugestao_id = str(uuid.uuid4())
        conn = self._get_connection()

        ini = _iso_com_fuso(inicio)
        f = _iso_com_fuso(fim)
        c_rs = quantizar_decimal(consumo_rs)
        g_min = quantizar_decimal(gasto_min)
        g_max = quantizar_decimal(gasto_max)
        reg_txt = regiao_texto or regiao_ra
        vibes_str = json.dumps(vibes or [], ensure_ascii=False)
        por_part_str = json.dumps(por_participante or {}, ensure_ascii=False)

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sugestoes_role (
                        id, sala_id, posicao, letra_card, local_id, nome_local, tipo, regiao_ra, regiao_texto, endereco,
                        inicio, fim, horario_texto, horario_situacao, contagem, consumo_rs, gasto_min, gasto_max,
                        tempo_medio_min, tempo_max_min, nota_justica, pontuacao, explicacao, tiktok_url, fonte,
                        vibes_json, por_participante_json
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s,
                        %s, %s
                    );
                    """,
                    (
                        sugestao_id, sala["id"], posicao, letra_card, local_id, nome_local, tipo, regiao_ra, reg_txt, endereco,
                        ini, f, horario_texto, horario_situacao, contagem, c_rs, g_min, g_max,
                        tempo_medio_min, tempo_max_min, nota_justica, pontuacao, explicacao, tiktok_url, fonte,
                        vibes_str, por_part_str,
                    ),
                )
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sugestoes_role (
                    id, sala_id, posicao, letra_card, local_id, nome_local, tipo, regiao_ra, regiao_texto, endereco,
                    inicio, fim, horario_texto, horario_situacao, contagem, consumo_rs, gasto_min, gasto_max,
                    tempo_medio_min, tempo_max_min, nota_justica, pontuacao, explicacao, tiktok_url, fonte,
                    vibes_json, por_participante_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    sugestao_id, sala["id"], posicao, letra_card, local_id, nome_local, tipo, regiao_ra, reg_txt, endereco,
                    ini, f, horario_texto, horario_situacao, contagem, str(c_rs), str(g_min), str(g_max),
                    tempo_medio_min, tempo_max_min, nota_justica, pontuacao, explicacao, tiktok_url, fonte,
                    vibes_str, por_part_str,
                ),
            )
            conn.commit()

        return {
            "id": sugestao_id,
            "sala_id": sala["id"],
            "local_id": local_id,
            "nome_local": nome_local,
            "consumo_rs": c_rs,
        }

    def salvar_sugestoes(self, codigo_sala: str, sugestoes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Salva uma lista completa de 3 a 4 cartões de sugestão."""
        resultado = []
        agora = datetime.now(timezone.utc)
        for idx, s in enumerate(sugestoes, start=1):
            res = self.adicionar_sugestao(
                codigo_sala=codigo_sala,
                local_id=s.get("local_id", f"LOC_{idx}"),
                nome_local=s["nome_local"],
                regiao_ra=s.get("regiao_ra", "Plano Piloto"),
                endereco=s.get("endereco", "Endereço no DF"),
                inicio=s.get("inicio", agora),
                fim=s.get("fim", agora),
                horario_texto=s.get("dia_horario_sugerido", "Horário a combinar"),
                consumo_rs=s.get("faixa_gasto_rs", Decimal("50.00")),
                gasto_min=s.get("gasto_min", Decimal("50.00")),
                gasto_max=s.get("gasto_max", Decimal("60.00")),
                explicacao=s.get("motivo_escolha", "Boa opção para o grupo"),
                posicao=idx,
                letra_card=chr(64 + idx),
                nota_justica=float(s.get("ranking_justica", 9.0)),
            )
            resultado.append(res)
        return resultado

    def listar_sugestoes_sala(self, codigo_sala: str) -> List[Dict[str, Any]]:
        """Retorna todas as opções de rolê sugeridas para a sala."""
        sala = self.obter_sala(codigo_sala)
        if not sala:
            return []

        conn = self._get_connection()
        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM sugestoes_role WHERE sala_id = %s ORDER BY posicao ASC;", (sala["id"],))
                return [dict(r) for r in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sugestoes_role WHERE sala_id = ? ORDER BY posicao ASC;", (sala["id"],))
            return [dict(r) for r in cur.fetchall()]

    def registrar_voto(self, codigo_sala: str, participante_id: str, sugestao_id: str) -> bool:
        """Registra voto garantindo que o participante e a sugestão pertencem à mesma sala."""
        sala = self.obter_sala(codigo_sala)
        if not sala:
            return False

        conn = self._get_connection()
        voto_id = str(uuid.uuid4())

        try:
            if self.is_postgres:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO votos (id, sala_id, participante_id, sugestao_id)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (participante_id, sugestao_id) DO NOTHING;
                        """,
                        (voto_id, sala["id"], participante_id, sugestao_id),
                    )
            else:
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT OR IGNORE INTO votos (id, sala_id, participante_id, sugestao_id)
                    VALUES (?, ?, ?, ?);
                    """,
                    (voto_id, sala["id"], participante_id, sugestao_id),
                )
                conn.commit()
            return True
        except Exception:
            return False

    def contabilizar_votos(self, codigo_sala: str) -> List[Dict[str, Any]]:
        """Retorna o ranking de votos em cada sugestão da sala."""
        placar = self.obter_placar_votos(codigo_sala)
        return [{"sugestao_id": sid, "total_votos": total} for sid, total in placar.items()]

    def obter_placar_votos(self, codigo_sala: str) -> Dict[str, int]:
        """Calcula o total de votos em cada cartão de sugestão."""
        sala = self.obter_sala(codigo_sala)
        if not sala:
            return {}

        conn = self._get_connection()
        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT sugestao_id, COUNT(*) as total
                    FROM votos
                    WHERE sala_id = %s
                    GROUP BY sugestao_id;
                    """,
                    (sala["id"],),
                )
                return {str(r["sugestao_id"]): r["total"] for r in cur.fetchall()}
        else:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT sugestao_id, COUNT(*) as total
                FROM votos
                WHERE sala_id = ?
                GROUP BY sugestao_id;
                """,
                (sala["id"],),
            )
            return {str(r["sugestao_id"]): r["total"] for r in cur.fetchall()}

    # ==========================================================================
    # PÓS-ROLÊ, DIVISÃO DE CONTA E RATEIOS INDIVIDUAIS
    # ==========================================================================
    def registrar_despesa_pos_role(
        self,
        codigo_sala: str,
        pagador_nome: str,
        valor_total_rs: Union[Decimal, str, float, int],
        chave_pix: str,
        rateios: Optional[List[Dict[str, Any]]] = None,
        pagador_participante_id: Optional[str] = None,
        tipo_chave_pix: str = "aleatoria",
        itens: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Registra a despesa do rolê e os rateios individuais de cada devedor.
        Nota (Issue #45): A criptografia da chave_pix em repouso (pgcrypto/Vault)
        está planejada para a PR da Tela 4 / Finanças.
        """
        sala = self.obter_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala '{codigo_sala}' não encontrada.")

        despesa_id = str(uuid.uuid4())
        total = quantizar_decimal(valor_total_rs)
        rateios_lista = rateios or []
        conn = self._get_connection()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO despesas_pos_role (id, sala_id, pagador_participante_id, pagador_nome, valor_total_rs, chave_pix, tipo_chave_pix, itens_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (despesa_id, sala["id"], pagador_participante_id, pagador_nome, total, chave_pix, tipo_chave_pix, json.dumps(itens or [])),
                )
                for r in rateios_lista:
                    cur.execute(
                        """
                        INSERT INTO despesa_rateios (id, despesa_id, devedor_participante_id, valor, pago_em)
                        VALUES (%s, %s, %s, %s, %s);
                        """,
                        (str(uuid.uuid4()), despesa_id, r["devedor_participante_id"], quantizar_decimal(r["valor"]), r.get("pago_em")),
                    )
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO despesas_pos_role (id, sala_id, pagador_participante_id, pagador_nome, valor_total_rs, chave_pix, tipo_chave_pix, itens_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (despesa_id, sala["id"], pagador_participante_id, pagador_nome, str(total), chave_pix, tipo_chave_pix, json.dumps(itens or [])),
            )
            for r in rateios_lista:
                cur.execute(
                    """
                    INSERT INTO despesa_rateios (id, despesa_id, devedor_participante_id, valor, pago_em)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (str(uuid.uuid4()), despesa_id, r["devedor_participante_id"], str(quantizar_decimal(r["valor"])), r.get("pago_em")),
                )
            conn.commit()

        return {
            "id": despesa_id,
            "sala_id": sala["id"],
            "valor_total_rs": total,
            "chave_pix": chave_pix,
            "rateios_count": len(rateios_lista),
        }

    def dar_baixa_rateio(self, despesa_id: str, devedor_participante_id: str) -> bool:
        """Marca o rateio de um amigo como quitado ao pagar via Pix."""
        conn = self._get_connection()
        agora = datetime.now(timezone.utc).isoformat()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE despesa_rateios
                    SET pago_em = %s
                    WHERE despesa_id = %s AND devedor_participante_id = %s;
                    """,
                    (agora, despesa_id, devedor_participante_id),
                )
                return cur.rowcount > 0
        else:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE despesa_rateios
                SET pago_em = ?
                WHERE despesa_id = ? AND devedor_participante_id = ?;
                """,
                (agora, despesa_id, devedor_participante_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def obter_despesas_sala(self, codigo_sala: str) -> List[Dict[str, Any]]:
        """Recupera despesas e rateios da sala."""
        sala = self.obter_sala(codigo_sala)
        if not sala:
            return []

        conn = self._get_connection()
        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM despesas_pos_role WHERE sala_id = %s;", (sala["id"],))
                return [dict(r) for r in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM despesas_pos_role WHERE sala_id = ?;", (sala["id"],))
            return [dict(r) for r in cur.fetchall()]

    # ==========================================================================
    # USUÁRIOS E ENDEREÇOS SALVOS
    # ==========================================================================
    def cadastrar_usuario(
        self,
        nome: str,
        maior_18_anos: bool = True,
        email: Optional[str] = None,
        telefone: Optional[str] = None,
        transporte_padrao: str = "misto",
        restricoes_permanentes: Optional[str] = None,
        chave_pix_padrao: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cadastra usuário respeitando a checagem obrigatória de 18+ anos."""
        if not maior_18_anos:
            raise ValueError("O Orquestrador de Rolês é exclusivo para maiores de 18 anos.")

        self.garantir_schema()
        usuario_id = str(uuid.uuid4())
        conn = self._get_connection()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO usuarios (id, nome, email, telefone, maior_18_anos, transporte_padrao, restricoes_permanentes, chave_pix_padrao)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, nome, email, maior_18_anos;
                    """,
                    (usuario_id, nome, email, telefone, maior_18_anos, transporte_padrao, restricoes_permanentes, chave_pix_padrao),
                )
                return cur.fetchone()
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO usuarios (id, nome, email, telefone, maior_18_anos, transporte_padrao, restricoes_permanentes, chave_pix_padrao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (usuario_id, nome, email, telefone, 1 if maior_18_anos else 0, transporte_padrao, restricoes_permanentes, chave_pix_padrao),
            )
            conn.commit()
            return {"id": usuario_id, "nome": nome, "email": email, "maior_18_anos": True}

    def adicionar_endereco_usuario(
        self,
        usuario_id: str,
        rotulo: str,
        regiao_ra: str,
        ponto_referencia: Optional[str] = None,
        is_padrao: bool = False,
    ) -> Dict[str, Any]:
        """Salva um endereço frequente do usuário no DF."""
        endereco_id = str(uuid.uuid4())
        conn = self._get_connection()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO usuario_enderecos (id, usuario_id, rotulo, regiao_ra, ponto_referencia, is_padrao)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (endereco_id, usuario_id, rotulo, regiao_ra, ponto_referencia, is_padrao),
                )
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO usuario_enderecos (id, usuario_id, rotulo, regiao_ra, ponto_referencia, is_padrao)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (endereco_id, usuario_id, rotulo, regiao_ra, ponto_referencia, 1 if is_padrao else 0),
            )
            conn.commit()

        return {"id": endereco_id, "usuario_id": usuario_id, "rotulo": rotulo, "regiao_ra": regiao_ra}

    def listar_enderecos_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        """Lista os endereços salvos do usuário ordenados com o padrão no topo."""
        conn = self._get_connection()
        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM usuario_enderecos WHERE usuario_id = %s ORDER BY is_padrao DESC;",
                    (usuario_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM usuario_enderecos WHERE usuario_id = ? ORDER BY is_padrao DESC;",
                (usuario_id,),
            )
            return [dict(r) for r in cur.fetchall()]


# ==============================================================================
# IMPLEMENTAÇÃO DA INTERFACE REPOSITÓRIO (COMPATÍVEL COM src/state.py - PR #48)
# ==============================================================================

class RepositorioSupabase(Repositorio):
    """
    Adaptador de persistência de salas para o Supabase / PostgreSQL,
    implementando integralmente a interface Repositorio de src/state.py:
    - existe(codigo: str) -> bool
    - obter(codigo: str) -> Sala | None
    - salvar(sala: Sala) -> None

    Persiste e reconstrói de forma transacional o agregado completo `Sala`:
    participantes (com PerfilInterpretado e token_hash), janelas_comuns,
    cartões de sugestão (`sugestoes_role`), votos (`votos`), status e resultado.
    """

    def __init__(self, cliente: Optional[SupabaseClient] = None):
        self.cliente = cliente or SupabaseClient()

    def existe(self, codigo: str) -> bool:
        if not codigo:
            return False
        return self.cliente.obter_sala(codigo.strip().upper()) is not None

    def salvar(self, sala: Sala) -> None:
        """Grava o estado completo da Sala nas tabelas normalizadas de forma transacional."""
        if not isinstance(sala, Sala):
            raise TypeError(f"RepositorioSupabase.salvar espera um objeto Sala, recebeu {type(sala).__name__}.")

        self.cliente.garantir_schema()
        conn = self.cliente._get_connection()
        codigo = sala.codigo.strip().upper()

        existente = self.cliente.obter_sala(codigo)
        sala_id = str(existente["id"]) if existente else _uuid_deterministico("sala", codigo, codigo)

        criado_iso = _iso_com_fuso(sala.criado_em)
        agora_iso = _iso_com_fuso(datetime.now(FUSO_BRASILIA))
        expira_iso = _iso_com_fuso(sala.criado_em + timedelta(days=30))

        janela_ini_iso = _iso_com_fuso(sala.janelas_comuns[0].inicio) if sala.janelas_comuns else None
        janela_fim_iso = _iso_com_fuso(sala.janelas_comuns[0].fim) if sala.janelas_comuns else None

        janelas_comuns_str = json.dumps(
            [
                {
                    "inicio": jc.inicio.isoformat(),
                    "fim": jc.fim.isoformat(),
                    "presentes": sorted(jc.presentes),
                    "total": jc.total,
                }
                for jc in sala.janelas_comuns
            ],
            ensure_ascii=False,
        )

        resultado_str = (
            json.dumps(
                {
                    "sugestao_id": sala.resultado.sugestao_id,
                    "votos": sala.resultado.votos,
                    "desempate_por_justica": sala.resultado.desempate_por_justica,
                    "mensagem": sala.resultado.mensagem,
                    "resumo_whatsapp": sala.resultado.resumo_whatsapp,
                    "fechado_em": sala.resultado.fechado_em.isoformat(),
                },
                ensure_ascii=False,
            )
            if sala.resultado is not None
            else None
        )
        avisos_str = json.dumps(list(sala.avisos), ensure_ascii=False)

        # Mapeamento determinístico de IDs de domínio (pid e s.id) para UUIDs relacionais
        mapa_part_uuid: Dict[str, str] = {
            pid: _uuid_deterministico("part", sala_id, pid) for pid in sala.participantes
        }
        mapa_sug_uuid: Dict[str, str] = {
            s.id: _uuid_deterministico("sug", sala_id, s.id) for s in sala.sugestoes
        }
        vencedora_uuid = (
            mapa_sug_uuid.get(sala.resultado.sugestao_id) if sala.resultado is not None else None
        )

        if self.cliente.is_postgres:
            with conn.transaction():
                with conn.cursor() as cur:
                    # 1. Upsert da sala (zera sugestao_vencedora_id temporariamente para atualizar sugestões sem conflito FK)
                    cur.execute(
                        """
                        INSERT INTO salas (
                            id, codigo_sala, nome_role, organizador_nome, token_organizador_hash,
                            status, janela_escolhida_inicio, janela_escolhida_fim, sugestao_vencedora_id,
                            janelas_comuns_json, resultado_json, avisos_json, expira_em, criado_em, atualizado_em
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (codigo_sala) DO UPDATE SET
                            nome_role = EXCLUDED.nome_role,
                            organizador_nome = EXCLUDED.organizador_nome,
                            token_organizador_hash = EXCLUDED.token_organizador_hash,
                            status = EXCLUDED.status,
                            janela_escolhida_inicio = EXCLUDED.janela_escolhida_inicio,
                            janela_escolhida_fim = EXCLUDED.janela_escolhida_fim,
                            sugestao_vencedora_id = NULL,
                            janelas_comuns_json = EXCLUDED.janelas_comuns_json,
                            resultado_json = EXCLUDED.resultado_json,
                            avisos_json = EXCLUDED.avisos_json,
                            atualizado_em = EXCLUDED.atualizado_em;
                        """,
                        (
                            sala_id, codigo, sala.nome_role, sala.organizador_nome, sala.token_organizador_hash,
                            sala.status, janela_ini_iso, janela_fim_iso,
                            janelas_comuns_str, resultado_str, avisos_str, expira_iso, criado_iso, agora_iso,
                        ),
                    )

                    # 2. Limpa votos anteriores da sala (serão reinseridos com o estado atual)
                    cur.execute("DELETE FROM votos WHERE sala_id = %s;", (sala_id,))

                    # 3. Sincroniza participantes e janelas individuais
                    uuids_atuais_part = list(mapa_part_uuid.values())
                    if uuids_atuais_part:
                        cur.execute(
                            "DELETE FROM sala_participantes WHERE sala_id = %s AND NOT (id = ANY(%s::uuid[]));",
                            (sala_id, uuids_atuais_part),
                        )
                    else:
                        cur.execute("DELETE FROM sala_participantes WHERE sala_id = %s;", (sala_id,))

                    for pid, p in sala.participantes.items():
                        p_uuid = mapa_part_uuid[pid]
                        pf = p.perfil
                        teto_val = quantizar_decimal(pf.teto) if (pf and pf.teto is not None) else None
                        vibe_str = ", ".join(pf.preferencias.tipos + pf.preferencias.vibes)[:200] if pf else None
                        transp_str = "/".join(pf.preferencias.transporte)[:40] if pf else None
                        perfil_str = self._serializar_perfil(pf) if pf else None
                        resp_iso = _iso_com_fuso(p.criado_em or sala.criado_em)

                        cur.execute(
                            """
                            INSERT INTO sala_participantes (
                                id, codigo_participante, sala_id, nome, token_hash,
                                confirmado, limite_gasto_rs, vibe_hoje, transporte_hoje, perfil_json, respondeu_em
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                codigo_participante = EXCLUDED.codigo_participante,
                                nome = EXCLUDED.nome,
                                token_hash = EXCLUDED.token_hash,
                                confirmado = EXCLUDED.confirmado,
                                limite_gasto_rs = EXCLUDED.limite_gasto_rs,
                                vibe_hoje = EXCLUDED.vibe_hoje,
                                transporte_hoje = EXCLUDED.transporte_hoje,
                                perfil_json = EXCLUDED.perfil_json,
                                respondeu_em = EXCLUDED.respondeu_em;
                            """,
                            (
                                p_uuid, pid, sala_id, p.nome, p.token_hash,
                                bool(p.confirmado), teto_val, vibe_str, transp_str, perfil_str, resp_iso,
                            ),
                        )

                        cur.execute("DELETE FROM participante_janelas WHERE participante_id = %s;", (p_uuid,))
                        if pf and pf.janelas:
                            ra_orig = pf.ra or "Não informada"
                            for j in pf.janelas:
                                cur.execute(
                                    """
                                    INSERT INTO participante_janelas (id, participante_id, inicio, fim, disponivel, ra_origem)
                                    VALUES (%s, %s, %s, %s, %s, %s);
                                    """,
                                    (
                                        str(uuid.uuid4()),
                                        p_uuid,
                                        _iso_com_fuso(j.inicio),
                                        _iso_com_fuso(j.fim),
                                        bool(j.disponivel),
                                        ra_orig,
                                    ),
                                )

                    # 4. Sincroniza sugestões de rolê
                    cur.execute("DELETE FROM sugestoes_role WHERE sala_id = %s;", (sala_id,))
                    for s in sala.sugestoes:
                        s_uuid = mapa_sug_uuid[s.id]
                        cur.execute(
                            """
                            INSERT INTO sugestoes_role (
                                id, sala_id, posicao, letra_card, local_id, nome_local, tipo,
                                regiao_ra, regiao_texto, endereco, inicio, fim, horario_texto,
                                horario_situacao, contagem, consumo_rs, gasto_min, gasto_max,
                                tempo_medio_min, tempo_max_min, nota_justica, pontuacao,
                                explicacao, tiktok_url, fonte, vibes_json, por_participante_json
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s, %s
                            );
                            """,
                            (
                                s_uuid, sala_id, s.posicao, s.id, s.lugar_id, s.nome, s.tipo,
                                s.ra or s.regiao_texto, s.regiao_texto, s.endereco,
                                _iso_com_fuso(s.inicio), _iso_com_fuso(s.fim), s.horario_texto,
                                s.horario_situacao, s.contagem,
                                quantizar_decimal(s.consumo_rs), quantizar_decimal(s.gasto_min), quantizar_decimal(s.gasto_max),
                                s.tempo_medio_min, s.tempo_max_min, float(s.nota_justica), float(s.pontuacao),
                                s.explicacao, s.tiktok_url, s.fonte,
                                json.dumps(s.vibes, ensure_ascii=False),
                                json.dumps(s.por_participante, ensure_ascii=False),
                            ),
                        )

                    # 5. Insere votos atuais
                    for pid, opcoes in sala.votos.items():
                        p_uuid = mapa_part_uuid.get(pid)
                        if not p_uuid:
                            continue
                        for letra in opcoes:
                            s_uuid = mapa_sug_uuid.get(letra)
                            if not s_uuid:
                                continue
                            cur.execute(
                                """
                                INSERT INTO votos (id, sala_id, participante_id, sugestao_id)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (participante_id, sugestao_id) DO NOTHING;
                                """,
                                (str(uuid.uuid4()), sala_id, p_uuid, s_uuid),
                            )

                    # 6. Atualiza sugestao_vencedora_id se houver resultado
                    if vencedora_uuid:
                        cur.execute(
                            "UPDATE salas SET sugestao_vencedora_id = %s WHERE id = %s;",
                            (vencedora_uuid, sala_id),
                        )
        else:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO salas (
                        id, codigo_sala, nome_role, organizador_nome, token_organizador_hash,
                        status, janela_escolhida_inicio, janela_escolhida_fim, sugestao_vencedora_id,
                        janelas_comuns_json, resultado_json, avisos_json, expira_em, criado_em, atualizado_em
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (codigo_sala) DO UPDATE SET
                        nome_role = excluded.nome_role,
                        organizador_nome = excluded.organizador_nome,
                        token_organizador_hash = excluded.token_organizador_hash,
                        status = excluded.status,
                        janela_escolhida_inicio = excluded.janela_escolhida_inicio,
                        janela_escolhida_fim = excluded.janela_escolhida_fim,
                        sugestao_vencedora_id = NULL,
                        janelas_comuns_json = excluded.janelas_comuns_json,
                        resultado_json = excluded.resultado_json,
                        avisos_json = excluded.avisos_json,
                        atualizado_em = excluded.atualizado_em;
                    """,
                    (
                        sala_id, codigo, sala.nome_role, sala.organizador_nome, sala.token_organizador_hash,
                        sala.status, janela_ini_iso, janela_fim_iso,
                        janelas_comuns_str, resultado_str, avisos_str, expira_iso, criado_iso, agora_iso,
                    ),
                )

                cur.execute("DELETE FROM votos WHERE sala_id = ?;", (sala_id,))

                uuids_atuais_part = list(mapa_part_uuid.values())
                if uuids_atuais_part:
                    placeholders = ",".join("?" for _ in uuids_atuais_part)
                    cur.execute(
                        f"DELETE FROM sala_participantes WHERE sala_id = ? AND id NOT IN ({placeholders});",
                        [sala_id, *uuids_atuais_part],
                    )
                else:
                    cur.execute("DELETE FROM sala_participantes WHERE sala_id = ?;", (sala_id,))

                for pid, p in sala.participantes.items():
                    p_uuid = mapa_part_uuid[pid]
                    pf = p.perfil
                    teto_val = str(quantizar_decimal(pf.teto)) if (pf and pf.teto is not None) else None
                    vibe_str = ", ".join(pf.preferencias.tipos + pf.preferencias.vibes)[:200] if pf else None
                    transp_str = "/".join(pf.preferencias.transporte)[:40] if pf else None
                    perfil_str = self._serializar_perfil(pf) if pf else None
                    resp_iso = _iso_com_fuso(p.criado_em or sala.criado_em)

                    cur.execute(
                        """
                        INSERT INTO sala_participantes (
                            id, codigo_participante, sala_id, nome, token_hash,
                            confirmado, limite_gasto_rs, vibe_hoje, transporte_hoje, perfil_json, respondeu_em
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO UPDATE SET
                            codigo_participante = excluded.codigo_participante,
                            nome = excluded.nome,
                            token_hash = excluded.token_hash,
                            confirmado = excluded.confirmado,
                            limite_gasto_rs = excluded.limite_gasto_rs,
                            vibe_hoje = excluded.vibe_hoje,
                            transporte_hoje = excluded.transporte_hoje,
                            perfil_json = excluded.perfil_json,
                            respondeu_em = excluded.respondeu_em;
                        """,
                        (
                            p_uuid, pid, sala_id, p.nome, p.token_hash,
                            1 if p.confirmado else 0, teto_val, vibe_str, transp_str, perfil_str, resp_iso,
                        ),
                    )

                    cur.execute("DELETE FROM participante_janelas WHERE participante_id = ?;", (p_uuid,))
                    if pf and pf.janelas:
                        ra_orig = pf.ra or "Não informada"
                        for j in pf.janelas:
                            cur.execute(
                                """
                                INSERT INTO participante_janelas (id, participante_id, inicio, fim, disponivel, ra_origem)
                                VALUES (?, ?, ?, ?, ?, ?);
                                """,
                                (
                                    str(uuid.uuid4()),
                                    p_uuid,
                                    _iso_com_fuso(j.inicio),
                                    _iso_com_fuso(j.fim),
                                    1 if j.disponivel else 0,
                                    ra_orig,
                                ),
                            )

                cur.execute("DELETE FROM sugestoes_role WHERE sala_id = ?;", (sala_id,))
                for s in sala.sugestoes:
                    s_uuid = mapa_sug_uuid[s.id]
                    cur.execute(
                        """
                        INSERT INTO sugestoes_role (
                            id, sala_id, posicao, letra_card, local_id, nome_local, tipo,
                            regiao_ra, regiao_texto, endereco, inicio, fim, horario_texto,
                            horario_situacao, contagem, consumo_rs, gasto_min, gasto_max,
                            tempo_medio_min, tempo_max_min, nota_justica, pontuacao,
                            explicacao, tiktok_url, fonte, vibes_json, por_participante_json
                        ) VALUES (
                            ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?, ?, ?
                        );
                        """,
                        (
                            s_uuid, sala_id, s.posicao, s.id, s.lugar_id, s.nome, s.tipo,
                            s.ra or s.regiao_texto, s.regiao_texto, s.endereco,
                            _iso_com_fuso(s.inicio), _iso_com_fuso(s.fim), s.horario_texto,
                            s.horario_situacao, s.contagem,
                            str(quantizar_decimal(s.consumo_rs)),
                            str(quantizar_decimal(s.gasto_min)),
                            str(quantizar_decimal(s.gasto_max)),
                            s.tempo_medio_min, s.tempo_max_min, float(s.nota_justica), float(s.pontuacao),
                            s.explicacao, s.tiktok_url, s.fonte,
                            json.dumps(s.vibes, ensure_ascii=False),
                            json.dumps(s.por_participante, ensure_ascii=False),
                        ),
                    )

                for pid, opcoes in sala.votos.items():
                    p_uuid = mapa_part_uuid.get(pid)
                    if not p_uuid:
                        continue
                    for letra in opcoes:
                        s_uuid = mapa_sug_uuid.get(letra)
                        if not s_uuid:
                            continue
                        cur.execute(
                            """
                            INSERT OR IGNORE INTO votos (id, sala_id, participante_id, sugestao_id)
                            VALUES (?, ?, ?, ?);
                            """,
                            (str(uuid.uuid4()), sala_id, p_uuid, s_uuid),
                        )

                if vencedora_uuid:
                    cur.execute(
                        "UPDATE salas SET sugestao_vencedora_id = ? WHERE id = ?;",
                        (vencedora_uuid, sala_id),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def obter(self, codigo: str) -> Sala | None:
        """Reconstrói e devolve o objeto Sala completo a partir das tabelas normalizadas."""
        if not codigo:
            return None
        dados_sala = self.cliente.obter_sala(codigo.strip().upper())
        if not dados_sala:
            return None

        sala_id = dados_sala["id"]
        conn = self.cliente._get_connection()

        if self.cliente.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM sala_participantes WHERE sala_id = %s ORDER BY respondeu_em ASC;",
                    (sala_id,),
                )
                rows_part = [dict(r) for r in cur.fetchall()]
                janelas_por_part: Dict[str, List[Dict[str, Any]]] = {}
                for rp in rows_part:
                    cur.execute(
                        "SELECT * FROM participante_janelas WHERE participante_id = %s ORDER BY inicio ASC;",
                        (rp["id"],),
                    )
                    janelas_por_part[str(rp["id"])] = [dict(j) for j in cur.fetchall()]

                cur.execute(
                    "SELECT * FROM sugestoes_role WHERE sala_id = %s ORDER BY posicao ASC;",
                    (sala_id,),
                )
                rows_sug = [dict(r) for r in cur.fetchall()]

                cur.execute(
                    "SELECT participante_id, sugestao_id FROM votos WHERE sala_id = %s ORDER BY votado_em ASC;",
                    (sala_id,),
                )
                rows_votos = [dict(r) for r in cur.fetchall()]
        else:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM sala_participantes WHERE sala_id = ? ORDER BY respondeu_em ASC;",
                (sala_id,),
            )
            rows_part = [dict(r) for r in cur.fetchall()]
            janelas_por_part = {}
            for rp in rows_part:
                cur.execute(
                    "SELECT * FROM participante_janelas WHERE participante_id = ? ORDER BY inicio ASC;",
                    (rp["id"],),
                )
                janelas_por_part[str(rp["id"])] = [dict(j) for j in cur.fetchall()]

            cur.execute(
                "SELECT * FROM sugestoes_role WHERE sala_id = ? ORDER BY posicao ASC;",
                (sala_id,),
            )
            rows_sug = [dict(r) for r in cur.fetchall()]

            cur.execute(
                "SELECT participante_id, sugestao_id FROM votos WHERE sala_id = ? ORDER BY votado_em ASC;",
                (sala_id,),
            )
            rows_votos = [dict(r) for r in cur.fetchall()]

        # 1. Reconstrói participantes e mapa UUID -> pid
        participantes: Dict[str, Participante] = {}
        uuid_para_pid: Dict[str, str] = {}
        for rp in rows_part:
            p_uuid = str(rp["id"])
            pid = str(rp.get("codigo_participante") or p_uuid)
            uuid_para_pid[p_uuid] = pid

            janelas_db = janelas_por_part.get(p_uuid, [])
            perfil = self._deserializar_perfil(rp, janelas_db)
            participantes[pid] = Participante(
                id=pid,
                nome=rp["nome"],
                token_hash=rp["token_hash"],
                perfil=perfil,
                confirmado=bool(rp["confirmado"]),
                criado_em=_para_datetime_local(rp.get("respondeu_em")),
            )

        # 2. Reconstrói sugestões e mapa UUID -> letra_card
        sugestoes: List[Sugestao] = []
        uuid_para_letra: Dict[str, str] = {}
        for rs in rows_sug:
            s_uuid = str(rs["id"])
            letra = str(rs.get("letra_card") or "A")
            uuid_para_letra[s_uuid] = letra
            vibes = _decodificar_json(rs.get("vibes_json"), [])
            por_part = _decodificar_json(rs.get("por_participante_json"), {})
            ra_val = rs.get("regiao_ra")
            reg_txt = rs.get("regiao_texto") or ra_val or ""
            sugestoes.append(
                Sugestao(
                    id=letra,
                    posicao=int(rs.get("posicao") or 1),
                    lugar_id=str(rs["local_id"]),
                    nome=str(rs["nome_local"]),
                    tipo=str(rs.get("tipo") or "bar"),
                    ra=None if ra_val == reg_txt and "(" in str(reg_txt) else ra_val,
                    regiao_texto=str(reg_txt),
                    endereco=str(rs["endereco"]),
                    inicio=_para_datetime_local(rs["inicio"]),
                    fim=_para_datetime_local(rs["fim"]),
                    horario_texto=str(rs["horario_texto"]),
                    horario_situacao=str(rs.get("horario_situacao") or "aberto"),
                    contagem=str(rs.get("contagem") or "todos podem"),
                    consumo_rs=quantizar_decimal(rs["consumo_rs"]),
                    gasto_min=quantizar_decimal(rs["gasto_min"]),
                    gasto_max=quantizar_decimal(rs["gasto_max"]),
                    tempo_medio_min=int(rs["tempo_medio_min"]) if rs.get("tempo_medio_min") is not None else None,
                    tempo_max_min=int(rs["tempo_max_min"]) if rs.get("tempo_max_min") is not None else None,
                    nota_justica=float(rs.get("nota_justica") or 0.0),
                    pontuacao=float(rs.get("pontuacao") or 0.0),
                    explicacao=str(rs["explicacao"]),
                    tiktok_url=rs.get("tiktok_url"),
                    fonte=str(rs.get("fonte") or "2fa"),
                    vibes=list(vibes),
                    por_participante=dict(por_part),
                )
            )

        # 3. Reconstrói votos (pid -> [letra_card, ...])
        votos: Dict[str, List[str]] = {}
        for rv in rows_votos:
            pid = uuid_para_pid.get(str(rv["participante_id"]))
            letra = uuid_para_letra.get(str(rv["sugestao_id"]))
            if pid and letra:
                votos.setdefault(pid, [])
                if letra not in votos[pid]:
                    votos[pid].append(letra)

        # 4. Reconstrói janelas_comuns, resultado e avisos
        jc_raw = _decodificar_json(dados_sala.get("janelas_comuns_json"), [])
        janelas_comuns = [
            JanelaComum(
                inicio=_para_datetime_local(jc["inicio"]),
                fim=_para_datetime_local(jc["fim"]),
                presentes=frozenset(jc.get("presentes", [])),
                total=int(jc.get("total", len(participantes))),
            )
            for jc in jc_raw
        ]

        res_raw = _decodificar_json(dados_sala.get("resultado_json"), None)
        resultado = (
            Resultado(
                sugestao_id=str(res_raw["sugestao_id"]),
                votos=int(res_raw["votos"]),
                desempate_por_justica=bool(res_raw["desempate_por_justica"]),
                mensagem=str(res_raw["mensagem"]),
                resumo_whatsapp=str(res_raw["resumo_whatsapp"]),
                fechado_em=_para_datetime_local(res_raw["fechado_em"]),
            )
            if isinstance(res_raw, dict) and "sugestao_id" in res_raw
            else None
        )

        avisos = list(_decodificar_json(dados_sala.get("avisos_json"), []))

        return Sala(
            codigo=str(dados_sala["codigo_sala"]),
            nome_role=str(dados_sala["nome_role"]),
            organizador_nome=str(dados_sala["organizador_nome"]),
            token_organizador_hash=str(dados_sala["token_organizador_hash"]),
            criado_em=_para_datetime_local(dados_sala.get("criado_em")),
            status=str(dados_sala.get("status") or COLETANDO),
            participantes=participantes,
            janelas_comuns=janelas_comuns,
            sugestoes=sugestoes,
            votos=votos,
            resultado=resultado,
            avisos=avisos,
        )

    @staticmethod
    def _serializar_perfil(pf: PerfilInterpretado) -> str:
        p = pf.preferencias
        return json.dumps(
            {
                "ra": pf.ra,
                "regiao": pf.regiao,
                "preferencias": {
                    "tipos": p.tipos,
                    "vibes": p.vibes,
                    "restricoes": p.restricoes,
                    "transporte": p.transporte,
                    "pet": p.pet,
                    "texto_busca": p.texto_busca,
                },
                "pendencias": pf.pendencias,
                "resumo": pf.resumo,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _deserializar_perfil(rp: Dict[str, Any], janelas_db: List[Dict[str, Any]]) -> PerfilInterpretado:
        janelas = [
            JanelaResolvida(
                inicio=_para_datetime_local(j["inicio"]),
                fim=_para_datetime_local(j["fim"]),
                disponivel=bool(j.get("disponivel", True)),
            )
            for j in janelas_db
        ]
        teto = (
            quantizar_decimal(rp["limite_gasto_rs"])
            if rp.get("limite_gasto_rs") is not None
            else None
        )
        meta = _decodificar_json(rp.get("perfil_json"), None)
        if isinstance(meta, dict):
            pm = meta.get("preferencias", {})
            prefs = Preferencias(
                tipos=list(pm.get("tipos", [])),
                vibes=list(pm.get("vibes", [])),
                restricoes=list(pm.get("restricoes", [])),
                transporte=list(pm.get("transporte", [])),
                pet=bool(pm.get("pet", False)),
                texto_busca=str(pm.get("texto_busca", "")),
            )
            return PerfilInterpretado(
                ra=meta.get("ra"),
                regiao=meta.get("regiao"),
                janelas=janelas,
                teto=teto,
                preferencias=prefs,
                pendencias=dict(meta.get("pendencias", {})),
                resumo=str(meta.get("resumo", "")),
            )

        # Fallback caso o participante tenha sido inserido direto via SupabaseClient.adicionar_participante
        ra_fallback = janelas_db[0].get("ra_origem") if janelas_db else None
        transp = [t.strip() for t in str(rp.get("transporte_hoje") or "").split("/") if t.strip()]
        return PerfilInterpretado(
            ra=ra_fallback,
            regiao=ra_fallback,
            janelas=janelas,
            teto=teto,
            preferencias=Preferencias(
                transporte=transp,
                texto_busca=str(rp.get("vibe_hoje") or ""),
            ),
            pendencias={},
            resumo=str(rp.get("vibe_hoje") or ""),
        )


def checar_conexao_supabase() -> Dict[str, Any]:
    """Função utilitária para rotas FastAPI checarem status do Supabase."""
    cliente = SupabaseClient()
    res = cliente.checar_conexao()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if url and key and HTTPX_DISPONIVEL:
        try:
            r = httpx.get(
                f"{url.rstrip('/')}/rest/v1/",
                headers={"apikey": key, "Authorization": f"Bearer {key}"},
                timeout=5.0,
            )
            res["supabase_rest_status"] = r.status_code
        except Exception as e:
            res["supabase_rest_erro"] = str(e)

    return res


def obter_cliente_db(use_memory_fallback: bool = False) -> SupabaseClient:
    """Factory para instanciar o cliente sob demanda sem criar arquivos em import time."""
    return SupabaseClient(use_memory_fallback=use_memory_fallback)
