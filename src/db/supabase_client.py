"""
Cliente de Conexão com o Banco de Dados (PostgreSQL / Supabase)
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
Responsável: Maria Eduarda (DevOps & Backend)
Issue #41 | Referência: GUIA_OFICIAL_PROJETO.md

Implementa acesso resiliente ao PostgreSQL (Supabase na nuvem / Docker) via psycopg
com suporte completo às correções da revisão do PR #50 e preservando 100% das regras de negócio:
1. Conexão real com PostgreSQL via psycopg usando DATABASE_URL (sob demanda/lazy).
2. schema.sql como fonte única da verdade para a estrutura de tabelas.
3. RLS (Row Level Security) e sigilo orçamentário (RNF-01 e RNF-02): cabe_no_orcamento() e obter_menor_orcamento_sala().
4. Precisão monetária absoluta com Decimal (sem floats nos cálculos financeiros e Pix).
5. Timestamps e janelas com ponto de partida amarrado por janela de horário.
6. Rateio individualizado pós-rolê (despesa_rateios) com quitação por participante.
7. Identificação e segurança: token_hash, token_organizador_hash e expira_em (LGPD).
8. Interface RepositorioSupabase para integração direta com src/state.py (PR #48).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any, Dict, List, Optional, Union
import uuid

# Tenta importar psycopg para PostgreSQL real
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_DISPONIVEL = True
except ImportError:
    PSYCOPG_DISPONIVEL = False

# Tenta importar requests/httpx para checar endpoint REST do Supabase
try:
    import httpx
    HTTPX_DISPONIVEL = True
except ImportError:
    HTTPX_DISPONIVEL = False

# Caminhos padrão
SCHEMA_SQL_PATH = Path(__file__).parent / "schema.sql"
LOCAL_DB_PATH = Path("data/app_local.db")


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


class SupabaseClient:
    """
    Cliente de banco de dados do Orquestrador de Rolês.
    Opera com PostgreSQL nativo (psycopg) quando DATABASE_URL estiver configurada,
    ou fallback resiliente SQLite (em memória ou disco) para testes e desenvolvimento offline.
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        use_memory_fallback: bool = False,
        db_path: Optional[Path] = None,
    ):
        self.database_url = database_url or os.environ.get("DATABASE_URL")
        self.use_memory = use_memory_fallback
        self.db_path = db_path or LOCAL_DB_PATH
        
        self.is_postgres = bool(self.database_url and PSYCOPG_DISPONIVEL)
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
                    self._conn = sqlite3.connect(":memory:")
                    self._conn.row_factory = sqlite3.Row
                return self._conn
            else:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                if self._conn is None:
                    self._conn = sqlite3.connect(str(self.db_path))
                    self._conn.row_factory = sqlite3.Row
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
        """Converte comandos específicos do Postgres para execução limpa no SQLite de teste."""
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
            l = re.sub(r"DEFAULT \(NOW\(\) \+ INTERVAL '30 days'\)", "DEFAULT CURRENT_TIMESTAMP", l)
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
        """Testa conectividade com o banco de dados (PostgreSQL ou SQLite fallback)."""
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
    # GESTÃO DE SALAS (ROLE-XXXX)
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

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO salas (id, codigo_sala, nome_role, organizador_nome, token_organizador_hash, criador_id, status, criado_em, atualizado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, 'coletando', %s, %s)
                    RETURNING id, codigo_sala, nome_role, organizador_nome, status;
                    """,
                    (sala_id, codigo_sala, nome_role, nome_org, token_hash, criador_id, agora, agora),
                )
                return cur.fetchone()
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO salas (id, codigo_sala, nome_role, organizador_nome, token_organizador_hash, criador_id, status, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, 'coletando', ?, ?);
                """,
                (sala_id, codigo_sala, nome_role, nome_org, token_hash, criador_id, agora, agora),
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
        """Busca uma sala pelo código único ROLE-XXXX."""
        self.garantir_schema()
        conn = self._get_connection()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM salas WHERE codigo_sala = %s;", (codigo_sala,))
                row = cur.fetchone()
                return dict(row) if row else None
        else:
            cur = conn.cursor()
            cur.execute("SELECT * FROM salas WHERE codigo_sala = ?;", (codigo_sala,))
            row = cur.fetchone()
            return dict(row) if row else None

    # ==========================================================================
    # PARTICIPANTES & SIGILO ORÇAMENTÁRIO (RNF-01 / RNF-02)
    # ==========================================================================
    def adicionar_participante(
        self,
        codigo_sala: str,
        nome: str,
        limite_gasto_rs: Optional[Union[Decimal, str, float, int, List[Dict[str, Any]]]] = None,
        janelas: Optional[Union[List[Dict[str, Any]], Decimal, str, float, int]] = None,
        *args,
        token_hash: Optional[str] = None,
        usuario_id: Optional[str] = None,
        vibe_hoje: Optional[str] = None,
        transporte_hoje: Optional[str] = None,
        preferencias_transporte: Optional[str] = None,
        confirmado: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Adiciona a resposta de um participante guardando o orçamento com Decimal.
        Cria as janelas associadas com data e RA de origem.
        Suporta flexivelmente as assinaturas de chamada anteriores.
        """
        # Suporte a inversão de parâmetros posicionais (janelas vs limite_gasto_rs)
        if isinstance(limite_gasto_rs, list) and isinstance(janelas, (Decimal, int, float, str)):
            janelas, limite_gasto_rs = limite_gasto_rs, janelas

        teto_val = quantizar_decimal(limite_gasto_rs if isinstance(limite_gasto_rs, (Decimal, int, float, str)) else 50.00)
        janelas_lista = janelas if isinstance(janelas, list) else []
        transporte = transporte_hoje or preferencias_transporte or "misto"

        sala = self.obter_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala com código '{codigo_sala}' não encontrada.")

        sala_id = sala["id"]
        participante_id = str(uuid.uuid4())
        tok = token_hash or f"tok_{uuid.uuid4().hex[:16]}"
        conn = self._get_connection()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sala_participantes (id, sala_id, usuario_id, nome, token_hash, confirmado, limite_gasto_rs, vibe_hoje, transporte_hoje)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (participante_id, sala_id, usuario_id, nome, tok, confirmado, teto_val, vibe_hoje, transporte),
                )
                for j in janelas_lista:
                    inicio = j.get("inicio", datetime.now(timezone.utc).isoformat())
                    fim = j.get("fim", datetime.now(timezone.utc).isoformat())
                    ra = j.get("regiao_ra") or j.get("ra_origem", "Plano Piloto")
                    cur.execute(
                        """
                        INSERT INTO participante_janelas (id, participante_id, inicio, fim, disponivel, ra_origem)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (str(uuid.uuid4()), participante_id, inicio, fim, j.get("disponivel", True), ra),
                    )
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sala_participantes (id, sala_id, usuario_id, nome, token_hash, confirmado, limite_gasto_rs, vibe_hoje, transporte_hoje)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (participante_id, sala_id, usuario_id, nome, tok, int(confirmado), str(teto_val), vibe_hoje, transporte),
            )
            for j in janelas_lista:
                inicio = str(j.get("inicio", datetime.now(timezone.utc).isoformat()))
                fim = str(j.get("fim", datetime.now(timezone.utc).isoformat()))
                ra = j.get("regiao_ra") or j.get("ra_origem", "Plano Piloto")
                cur.execute(
                    """
                    INSERT INTO participante_janelas (id, participante_id, inicio, fim, disponivel, ra_origem)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        str(uuid.uuid4()),
                        participante_id,
                        inicio,
                        fim,
                        1 if j.get("disponivel", True) else 0,
                        ra,
                    ),
                )
            conn.commit()

        return {
            "id": participante_id,
            "sala_id": sala_id,
            "nome": nome,
            "confirmado": confirmado,
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
                    SELECT id, sala_id, nome, confirmado, vibe_hoje, transporte_hoje, respondeu_em, limite_gasto_rs
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
                SELECT id, sala_id, nome, confirmado, vibe_hoje, transporte_hoje, respondeu_em, limite_gasto_rs
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
        sala = self.obter_sala(codigo_sala)
        if not sala:
            return False

        custo = quantizar_decimal(custo_por_pessoa)
        conn = self._get_connection()

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT MIN(limite_gasto_rs) as min_teto
                    FROM sala_participantes
                    WHERE sala_id = %s;
                    """,
                    (sala["id"],),
                )
                row = cur.fetchone()
                if not row or row["min_teto"] is None:
                    return True
                return custo <= Decimal(str(row["min_teto"]))
        else:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT MIN(CAST(limite_gasto_rs AS REAL)) as min_teto
                FROM sala_participantes
                WHERE sala_id = ?;
                """,
                (sala["id"],),
            )
            row = cur.fetchone()
            if not row or row["min_teto"] is None:
                return True
            return custo <= Decimal(str(row["min_teto"])).quantize(Decimal("0.01"))

    def obter_menor_orcamento_sala(self, codigo_sala: str) -> Optional[Decimal]:
        """
        Retorna internamente o menor limite de gastos da sala para calibragem do RAG (RNF-01/02).
        Retorna em Decimal exato.
        """
        sala = self.obter_sala(codigo_sala)
        if not sala:
            return None

        conn = self._get_connection()
        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT MIN(limite_gasto_rs) as min_teto FROM sala_participantes WHERE sala_id = %s;",
                    (sala["id"],),
                )
                row = cur.fetchone()
                return Decimal(str(row["min_teto"])) if row and row["min_teto"] is not None else None
        else:
            cur = conn.cursor()
            cur.execute(
                "SELECT MIN(CAST(limite_gasto_rs AS REAL)) as min_teto FROM sala_participantes WHERE sala_id = ?;",
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
    ) -> Dict[str, Any]:
        """Salva um cartão de sugestão gerado pela IA com centavos exatos (Decimal)."""
        sala = self.obter_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala '{codigo_sala}' não encontrada.")

        sugestao_id = str(uuid.uuid4())
        conn = self._get_connection()

        ini = inicio.isoformat() if isinstance(inicio, datetime) else str(inicio)
        f = fim.isoformat() if isinstance(fim, datetime) else str(fim)
        c_rs = quantizar_decimal(consumo_rs)
        g_min = quantizar_decimal(gasto_min)
        g_max = quantizar_decimal(gasto_max)

        if self.is_postgres:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sugestoes_role (
                        id, sala_id, posicao, letra_card, local_id, nome_local, tipo, regiao_ra, endereco,
                        inicio, fim, horario_texto, consumo_rs, gasto_min, gasto_max,
                        nota_justica, explicacao, tiktok_url
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s
                    );
                    """,
                    (
                        sugestao_id, sala["id"], posicao, letra_card, local_id, nome_local, tipo, regiao_ra, endereco,
                        ini, f, horario_texto, c_rs, g_min, g_max,
                        nota_justica, explicacao, tiktok_url
                    ),
                )
        else:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO sugestoes_role (
                    id, sala_id, posicao, letra_card, local_id, nome_local, tipo, regiao_ra, endereco,
                    inicio, fim, horario_texto, consumo_rs, gasto_min, gasto_max,
                    nota_justica, explicacao, tiktok_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    sugestao_id, sala["id"], posicao, letra_card, local_id, nome_local, tipo, regiao_ra, endereco,
                    ini, f, horario_texto, str(c_rs), str(g_min), str(g_max),
                    nota_justica, explicacao, tiktok_url
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
        """Registra a despesa do rolê e os rateios individuais de cada devedor."""
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

class RepositorioSupabase:
    """
    Adaptador de persistência de salas para o Supabase / PostgreSQL,
    implementando a interface Repositorio de src/state.py:
    - existe(codigo: str) -> bool
    - obter(codigo: str) -> Sala | None
    - salvar(sala: Sala) -> None
    """

    def __init__(self, cliente: Optional[SupabaseClient] = None):
        self.cliente = cliente or SupabaseClient()

    def existe(self, codigo: str) -> bool:
        return self.cliente.obter_sala(codigo) is not None

    def obter(self, codigo: str) -> Optional[Any]:
        dados_sala = self.cliente.obter_sala(codigo)
        if not dados_sala:
            return None
        return dados_sala

    def salvar(self, sala: Any) -> None:
        codigo = getattr(sala, "codigo", getattr(sala, "codigo_sala", None))
        nome = getattr(sala, "nome_role", "Rolê")
        organizador = getattr(sala, "organizador_nome", getattr(sala, "criador_nome", "Organizador"))
        token_hash = getattr(sala, "token_organizador_hash", None)

        if not self.existe(codigo):
            self.cliente.criar_sala(
                codigo_sala=codigo,
                nome_role=nome,
                organizador_nome=organizador,
                token_organizador_hash=token_hash,
            )


def checar_conexao_supabase() -> Dict[str, Any]:
    """Função utilitária para rotas FastAPI checarem status do Supabase."""
    cliente = SupabaseClient()
    res = cliente.checar_conexao()
    
    # Se tiver SUPABASE_URL configurada, checa também o endpoint REST
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
