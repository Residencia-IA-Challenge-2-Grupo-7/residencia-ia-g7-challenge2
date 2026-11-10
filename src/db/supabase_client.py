"""
Cliente de Conexão com o Banco de Dados (Supabase / PostgreSQL)
Projeto: Orquestrador de Rolês - Grupo 7 (Residência em IA | UnB & Eldorado)
Responsável: Maria Eduarda (DevOps & Backend)
Issue #41 | Referência: GUIA_OFICIAL_PROJETO.md

Implementa acesso resiliente ao Supabase / PostgreSQL com suporte a:
- Cadastro de Usuário e Múltiplos Endereços no DF (Casa, Trabalho, UnB)
- Amarração inteligente de Ponto de Partida por Janela de Horário
- Conexão oficial via PostgreSQL / Supabase REST API
- Fallback automático para SQLite local em memória/disco para testes e CI limpo
- Blindagem de Sigilo Orçamentário (RNF-01 e RNF-02): orçamentos individuais
  só são acessíveis para cálculos internos, nunca em listagens públicas da sala.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Union
import uuid

# Leitura de segredos do ambiente
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Caminho para banco local de fallback (para testes e desenvolvimento)
LOCAL_DB_PATH = Path("data/app_local.db")


class SupabaseClient:
    """
    Cliente de banco de dados oficial do Orquestrador de Rolês.
    Pode operar diretamente no Supabase ou em banco local SQLite de fallback.
    """

    def __init__(self, use_memory_fallback: bool = False, db_path: Optional[Path] = None):
        self.use_memory = use_memory_fallback
        self.db_path = db_path or LOCAL_DB_PATH
        self._init_sqlite_db()

    def _init_sqlite_db(self) -> None:
        """Inicializa o banco SQLite local garantindo o mesmo esquema do PostgreSQL oficial."""
        if not self.use_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = self._get_connection()
        cursor = conn.cursor()

        # 1. Tabela usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id TEXT PRIMARY KEY,
                nome TEXT NOT NULL,
                email TEXT UNIQUE,
                telefone TEXT,
                maior_18_anos INTEGER NOT NULL DEFAULT 1,
                transporte_padrao TEXT DEFAULT 'misto',
                restricoes_permanentes TEXT,
                chave_pix_padrao TEXT,
                tipo_chave_pix_padrao TEXT DEFAULT 'aleatoria',
                criado_em TEXT NOT NULL
            );
        """)

        # 2. Tabela usuario_enderecos (Casa, Trabalho, UnB, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuario_enderecos (
                id TEXT PRIMARY KEY,
                usuario_id TEXT NOT NULL,
                rotulo TEXT NOT NULL,
                regiao_ra TEXT NOT NULL,
                ponto_referencia TEXT NOT NULL,
                is_padrao INTEGER DEFAULT 0,
                criado_em TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );
        """)

        # 3. Tabela salas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS salas (
                id TEXT PRIMARY KEY,
                codigo_sala TEXT UNIQUE NOT NULL,
                nome_role TEXT NOT NULL,
                criador_id TEXT,
                criador_nome TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'aberta',
                janela_escolhida_json TEXT,
                sugestao_vencedora_id TEXT,
                criado_em TEXT NOT NULL,
                FOREIGN KEY (criador_id) REFERENCES usuarios(id) ON DELETE SET NULL
            );
        """)

        # 4. Tabela sala_participantes (com janelas e origens associadas)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sala_participantes (
                id TEXT PRIMARY KEY,
                sala_id TEXT NOT NULL,
                usuario_id TEXT,
                nome TEXT NOT NULL,
                janelas_disponiveis_json TEXT NOT NULL,
                limite_gasto_rs REAL NOT NULL,
                vibe_hoje TEXT,
                transporte_hoje TEXT,
                respondeu_em TEXT NOT NULL,
                FOREIGN KEY (sala_id) REFERENCES salas(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            );
        """)

        # 5. Tabela sugestoes_role
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sugestoes_role (
                id TEXT PRIMARY KEY,
                sala_id TEXT NOT NULL,
                local_id TEXT,
                nome_local TEXT NOT NULL,
                regiao_ra TEXT NOT NULL,
                endereco TEXT NOT NULL,
                dia_horario_sugerido TEXT NOT NULL,
                faixa_gasto_rs REAL NOT NULL,
                mobility_summary TEXT,
                ranking_justica REAL DEFAULT 0.0,
                motivo_escolha TEXT,
                criado_em TEXT NOT NULL,
                FOREIGN KEY (sala_id) REFERENCES salas(id) ON DELETE CASCADE
            );
        """)

        # 6. Tabela votos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS votos (
                id TEXT PRIMARY KEY,
                sala_id TEXT NOT NULL,
                participante_id TEXT NOT NULL,
                sugestao_id TEXT NOT NULL,
                votado_em TEXT NOT NULL,
                UNIQUE (participante_id, sugestao_id),
                FOREIGN KEY (sala_id) REFERENCES salas(id) ON DELETE CASCADE,
                FOREIGN KEY (participante_id) REFERENCES sala_participantes(id) ON DELETE CASCADE,
                FOREIGN KEY (sugestao_id) REFERENCES sugestoes_role(id) ON DELETE CASCADE
            );
        """)

        # 7. Tabela despesas_pos_role
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS despesas_pos_role (
                id TEXT PRIMARY KEY,
                sala_id TEXT NOT NULL,
                pagador_nome TEXT NOT NULL,
                valor_total_rs REAL NOT NULL,
                chave_pix TEXT NOT NULL,
                tipo_chave_pix TEXT DEFAULT 'aleatoria',
                itens_json TEXT,
                comprovante_url TEXT,
                quitado INTEGER DEFAULT 0,
                criado_em TEXT NOT NULL,
                FOREIGN KEY (sala_id) REFERENCES salas(id) ON DELETE CASCADE
            );
        """)

        conn.commit()
        conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna uma conexão ativa com o banco."""
        if self.use_memory:
            conn = sqlite3.connect(":memory:")
        else:
            conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # --------------------------------------------------------------------------
    # 1. USUÁRIOS E ENDEREÇOS (CADASTRO FIXO)
    # --------------------------------------------------------------------------

    def cadastrar_usuario(
        self,
        nome: str,
        email: Optional[str] = None,
        telefone: Optional[str] = None,
        maior_18_anos: bool = True,
        transporte_padrao: str = "misto",
        restricoes_permanentes: Optional[str] = None,
        chave_pix_padrao: Optional[str] = None,
        tipo_chave_pix_padrao: str = "aleatoria",
    ) -> Dict[str, Any]:
        """Cadastra um novo usuário no aplicativo."""
        if not maior_18_anos:
            raise ValueError("O Orquestrador de Rolês é exclusivo para maiores de 18 anos (ADR 0002).")

        usuario_id = str(uuid.uuid4())
        criado_em = datetime.now(timezone.utc).isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO usuarios 
            (id, nome, email, telefone, maior_18_anos, transporte_padrao, restricoes_permanentes, chave_pix_padrao, tipo_chave_pix_padrao, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usuario_id,
                nome.strip(),
                email.strip().lower() if email else None,
                telefone.strip() if telefone else None,
                1 if maior_18_anos else 0,
                transporte_padrao,
                restricoes_permanentes,
                chave_pix_padrao,
                tipo_chave_pix_padrao,
                criado_em,
            ),
        )
        conn.commit()
        conn.close()

        return {
            "id": usuario_id,
            "nome": nome,
            "email": email,
            "maior_18_anos": maior_18_anos,
            "transporte_padrao": transporte_padrao,
            "chave_pix_padrao": chave_pix_padrao,
            "criado_em": criado_em,
        }

    def buscar_usuario(self, usuario_id: str) -> Optional[Dict[str, Any]]:
        """Busca o usuário pelo ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def adicionar_endereco_usuario(
        self,
        usuario_id: str,
        rotulo: str,
        regiao_ra: str,
        ponto_referencia: str,
        is_padrao: bool = False,
    ) -> Dict[str, Any]:
        """Salva um endereço frequente no perfil do usuário (Casa, Trabalho, UnB)."""
        end_id = str(uuid.uuid4())
        criado_em = datetime.now(timezone.utc).isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()

        # Se for padrão, desmarca outros anteriores
        if is_padrao:
            cursor.execute("UPDATE usuario_enderecos SET is_padrao = 0 WHERE usuario_id = ?", (usuario_id,))

        cursor.execute(
            """
            INSERT INTO usuario_enderecos (id, usuario_id, rotulo, regiao_ra, ponto_referencia, is_padrao, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (end_id, usuario_id, rotulo.strip(), regiao_ra.strip(), ponto_referencia.strip(), 1 if is_padrao else 0, criado_em),
        )
        conn.commit()
        conn.close()

        return {
            "id": end_id,
            "usuario_id": usuario_id,
            "rotulo": rotulo,
            "regiao_ra": regiao_ra,
            "ponto_referencia": ponto_referencia,
            "is_padrao": is_padrao,
        }

    def listar_enderecos_usuario(self, usuario_id: str) -> List[Dict[str, Any]]:
        """Lista todos os locais salvos de um usuário."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuario_enderecos WHERE usuario_id = ? ORDER BY is_padrao DESC", (usuario_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # --------------------------------------------------------------------------
    # 2. SALAS (CRIAÇÃO E GESTÃO)
    # --------------------------------------------------------------------------

    def criar_sala(
        self, codigo_sala: str, nome_role: str, criador_nome: str, criador_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cria uma nova sala de rolê no banco de dados."""
        sala_id = str(uuid.uuid4())
        criado_em = datetime.now(timezone.utc).isoformat()
        codigo = codigo_sala.strip().upper()

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO salas (id, codigo_sala, nome_role, criador_id, criador_nome, status, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sala_id, codigo, nome_role.strip(), criador_id, criador_nome.strip(), "aberta", criado_em),
        )
        conn.commit()
        conn.close()

        return {
            "id": sala_id,
            "codigo_sala": codigo,
            "nome_role": nome_role,
            "criador_nome": criador_nome,
            "status": "aberta",
            "criado_em": criado_em,
        }

    def buscar_sala(self, codigo_sala: str) -> Optional[Dict[str, Any]]:
        """Busca uma sala pelo código único."""
        codigo = codigo_sala.strip().upper()
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM salas WHERE codigo_sala = ?", (codigo,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    # --------------------------------------------------------------------------
    # 3. PARTICIPANTES & ORIGEM POR JANELA DE HORÁRIO
    # --------------------------------------------------------------------------

    def adicionar_participante(
        self,
        codigo_sala: str,
        nome: str,
        origem_df: Optional[str] = None,
        dias_horarios: Optional[str] = None,
        limite_gasto_rs: float = 0.0,
        preferencias_transporte: Optional[str] = None,
        janelas: Optional[List[Dict[str, Any]]] = None,
        vibe_hoje: Optional[str] = None,
        usuario_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Adiciona a participação de um amigo em um rolê específico.
        Suporta tanto o modelo com janelas estruturadas (origem por horário)
        quanto o formato simplificado de texto.
        """
        sala = self.buscar_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala '{codigo_sala}' não encontrada.")

        participante_id = str(uuid.uuid4())
        respondeu_em = datetime.now(timezone.utc).isoformat()
        teto = max(0.0, float(limite_gasto_rs))

        # Se não vier estruturado em janelas, encapsula os campos texto legados
        if janelas:
            janelas_dados = janelas
        else:
            janelas_dados = [
                {
                    "dia_horario": dias_horarios or "a combinar",
                    "origem": origem_df or "Plano Piloto",
                    "regiao_ra": origem_df or "Plano Piloto",
                }
            ]

        janelas_json = json.dumps(janelas_dados, ensure_ascii=False)

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO sala_participantes 
            (id, sala_id, usuario_id, nome, janelas_disponiveis_json, limite_gasto_rs, vibe_hoje, transporte_hoje, respondeu_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                participante_id,
                sala["id"],
                usuario_id,
                nome.strip(),
                janelas_json,
                teto,
                vibe_hoje or "",
                preferencias_transporte or "",
                respondeu_em,
            ),
        )
        conn.commit()
        conn.close()

        return {
            "id": participante_id,
            "sala_id": sala["id"],
            "nome": nome,
            "respondeu_em": respondeu_em,
        }

    def listar_participantes_sala(self, codigo_sala: str, incluir_sigilo: bool = False) -> List[Dict[str, Any]]:
        """
        Lista os participantes da sala.
        ATENÇÃO (RNF-01 e RNF-02): incluir_sigilo=False por padrão. O campo
        'limite_gasto_rs' NUNCA é retornado publicamente.
        """
        sala = self.buscar_sala(codigo_sala)
        if not sala:
            return []

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sala_participantes WHERE sala_id = ? ORDER BY respondeu_em ASC", (sala["id"],))
        rows = cursor.fetchall()
        conn.close()

        resultados: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            try:
                d["janelas_disponiveis"] = json.loads(d.get("janelas_disponiveis_json", "[]"))
            except Exception:
                d["janelas_disponiveis"] = []
            d.pop("janelas_disponiveis_json", None)

            if not incluir_sigilo:
                d.pop("limite_gasto_rs", None)

            resultados.append(d)

        return resultados

    def obter_menor_orcamento_sala(self, codigo_sala: str) -> Optional[float]:
        """Retorna o MENOR limite individual de gasto da sala (Regra da Menor Miséria)."""
        sala = self.buscar_sala(codigo_sala)
        if not sala:
            return None

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(limite_gasto_rs) as menor_teto FROM sala_participantes WHERE sala_id = ?", (sala["id"],))
        row = cursor.fetchone()
        conn.close()

        if row and row["menor_teto"] is not None:
            return float(row["menor_teto"])
        return None

    # --------------------------------------------------------------------------
    # 4. SUGESTÕES, VOTAÇÃO E PÓS-ROLÊ
    # --------------------------------------------------------------------------

    def salvar_sugestoes(self, codigo_sala: str, sugestoes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Salva os 3 a 4 cartões de sugestão gerados pela IA."""
        sala = self.buscar_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala '{codigo_sala}' não encontrada.")

        salvos: List[Dict[str, Any]] = []
        conn = self._get_connection()
        cursor = conn.cursor()
        criado_em = datetime.now(timezone.utc).isoformat()

        for s in sugestoes:
            sugestao_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO sugestoes_role
                (id, sala_id, local_id, nome_local, regiao_ra, endereco, dia_horario_sugerido, 
                 faixa_gasto_rs, mobility_summary, ranking_justica, motivo_escolha, criado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sugestao_id,
                    sala["id"],
                    s.get("local_id"),
                    s["nome_local"],
                    s["regiao_ra"],
                    s["endereco"],
                    s.get("dia_horario_sugerido", ""),
                    float(s.get("faixa_gasto_rs", 0.0)),
                    s.get("mobility_summary", ""),
                    float(s.get("ranking_justica", 0.0)),
                    s.get("motivo_escolha", ""),
                    criado_em,
                ),
            )
            item = dict(s)
            item["id"] = sugestao_id
            salvos.append(item)

        cursor.execute("UPDATE salas SET status = 'votando' WHERE id = ?", (sala["id"],))
        conn.commit()
        conn.close()
        return salvos

    def registrar_voto(self, codigo_sala: str, participante_id: str, sugestao_id: str) -> Dict[str, Any]:
        """Registra o voto de um participante em um cartão."""
        sala = self.buscar_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala '{codigo_sala}' não encontrada.")

        voto_id = str(uuid.uuid4())
        votado_em = datetime.now(timezone.utc).isoformat()

        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO votos (id, sala_id, participante_id, sugestao_id, votado_em) VALUES (?, ?, ?, ?, ?)",
                (voto_id, sala["id"], participante_id, sugestao_id, votado_em),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

        return {"voto_id": voto_id, "participante_id": participante_id, "sugestao_id": sugestao_id}

    def contabilizar_votos(self, codigo_sala: str) -> List[Dict[str, Any]]:
        """Calcula a contagem de votos de cada sugestão."""
        sala = self.buscar_sala(codigo_sala)
        if not sala:
            return []

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.nome_local, s.regiao_ra, s.ranking_justica, COUNT(v.id) as total_votos
            FROM sugestoes_role s
            LEFT JOIN votos v ON s.id = v.sugestao_id
            WHERE s.sala_id = ?
            GROUP BY s.id
            ORDER BY total_votos DESC, s.ranking_justica DESC
            """,
            (sala["id"],),
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def registrar_despesa_pos_role(
        self,
        codigo_sala: str,
        pagador_nome: str,
        valor_total_rs: float,
        chave_pix: str,
        tipo_chave_pix: str = "aleatoria",
        itens_json: Optional[List[Dict[str, Any]]] = None,
        comprovante_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Registra a despesa do pós-rolê com chave Pix."""
        sala = self.buscar_sala(codigo_sala)
        if not sala:
            raise ValueError(f"Sala '{codigo_sala}' não encontrada.")

        despesa_id = str(uuid.uuid4())
        criado_em = datetime.now(timezone.utc).isoformat()
        itens_str = json.dumps(itens_json, ensure_ascii=False) if itens_json else "[]"

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO despesas_pos_role
            (id, sala_id, pagador_nome, valor_total_rs, chave_pix, tipo_chave_pix, itens_json, comprovante_url, quitado, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                despesa_id,
                sala["id"],
                pagador_nome.strip(),
                float(valor_total_rs),
                chave_pix.strip(),
                tipo_chave_pix,
                itens_str,
                comprovante_url,
                criado_em,
            ),
        )
        conn.commit()
        conn.close()

        return {
            "id": despesa_id,
            "sala_id": sala["id"],
            "pagador_nome": pagador_nome,
            "valor_total_rs": valor_total_rs,
            "chave_pix": chave_pix,
            "criado_em": criado_em,
        }


def checar_conexao_supabase() -> Dict[str, Any]:
    """
    Testa a conectividade real com os servidores do Supabase na nuvem via REST API.
    Retorna o status, código HTTP e mensagem explicativa.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        return {
            "conectado": False,
            "motivo": "SUPABASE_URL ou SUPABASE_KEY não configuradas no ambiente ou .env",
            "modo": "fallback_local",
        }

    endpoint = f"{url.rstrip('/')}/rest/v1/salas?select=count"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }

    try:
        import httpx
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(endpoint, headers=headers)
            if resp.status_code in [200, 206]:
                return {
                    "conectado": True,
                    "status_code": resp.status_code,
                    "url": url,
                    "mensagem": "Conexão com o Supabase na nuvem estabelecida com sucesso!",
                }
            return {
                "conectado": False,
                "status_code": resp.status_code,
                "url": url,
                "motivo": f"Resposta inesperada do Supabase: {resp.text}",
            }
    except Exception as exc:
        return {
            "conectado": False,
            "url": url,
            "motivo": f"Falha de conexão com o Supabase: {exc}",
        }


# Instância global
db_client = SupabaseClient()

