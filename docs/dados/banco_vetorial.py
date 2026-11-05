import csv
import json
import math
import ssl
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from coletor_tiktok_2fa import (
    BANCO_APROVADO_FILE,
    DATA_DIR,
    QUARENTENA_FILE,
    load_env,
    load_json_list,
    save_json_list,
)

VECTOR_DB_FILE = DATA_DIR / "banco_vetorial_embeddings.json"
CSV_CLEAN_FILE = DATA_DIR / "banco_aprovado_2fa.csv"
CSV_VECTOR_FILE = DATA_DIR / "banco_vetorial_embeddings.csv"
SSL_CTX = ssl._create_unverified_context()


def gerar_embedding_gemini(texto: str, gem_key: str) -> Optional[List[float]]:
    """
    Converte o documento textual do local (Nome + Tipo + Vibes + Resumo + Áudio Whisper)
    em um Vetor Matemático real de 3.072 dimensões usando o modelo oficial
    models/gemini-embedding-001 da Google.
    """
    if not gem_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={gem_key}"
    payload = {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": texto[:2500]}]},
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("embedding", {}).get("values")
    except Exception:
        return None


def similaridade_cosseno(v1: List[float], v2: List[float]) -> float:
    """Calcula o cosseno do ângulo entre dois vetores no espaço multidimensional."""
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def montar_texto_para_vetorizacao(item: Dict[str, Any]) -> str:
    """
    Monta o 'Documento Semântico' que será transformado em números (Embedding).
    Reúne Nome, Tipo de Rolê, Vibes (incluindo Kid Friendly), Bairro, Preço e o Áudio do TikTok.
    """
    vibes_str = ", ".join(item.get("vibes", []))
    kid_str = "Sim, Kid Friendly (ótimo para crianças e família)." if item.get("kid_friendly") else ""
    return (
        f"Local: {item.get('nome')} | Categoria: {item.get('tipo_de_role')} | "
        f"Região: {item.get('regiao_administrativa')} ({item.get('endereco')}) | "
        f"Faixa de Preço: {item.get('faixa_de_preco')} (R$ {item.get('custo_medio_rs')}) | "
        f"Vibes: {vibes_str}. {kid_str} | "
        f"Experiência: {item.get('resumo_sensorial')} | "
        f"Relato do TikTok: {item.get('transcricao_audio_whisper', '')[:500]}"
    )


def exportar_csvs(registros_vetorizados: List[Dict[str, Any]]) -> None:
    """
    Exporta o banco de dados em dois formatos CSV para facilitar o trabalho da equipe:
    1. banco_aprovado_2fa.csv: Tabela limpa para Excel / Google Sheets / Pandas (sem os 3.072 números)
    2. banco_vetorial_embeddings.csv: Tabela completa incluindo a coluna embedding_vector (3.072 dimensões)
    """
    cols_clean = [
        "id",
        "nome",
        "tipo_de_role",
        "vibes",
        "kid_friendly",
        "evidencia_kid_friendly",
        "regiao_administrativa",
        "endereco",
        "lat",
        "lng",
        "faixa_de_preco",
        "custo_medio_rs",
        "tiktok_url",
        "data_publicacao",
        "horario_funcionamento",
        "resumo_sensorial",
        "transcricao_audio_whisper",
        "status_2fa",
    ]
    cols_vector = cols_clean + ["modelo_embedding", "dimensoes_vetor", "embedding_vector"]

    with open(CSV_CLEAN_FILE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols_clean)
        w.writeheader()
        for item in registros_vetorizados:
            row = {k: item.get(k, "") for k in cols_clean}
            if isinstance(row["vibes"], list):
                row["vibes"] = " | ".join(row["vibes"])
            w.writerow(row)

    with open(CSV_VECTOR_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols_vector)
        w.writeheader()
        for item in registros_vetorizados:
            row = {k: item.get(k, "") for k in cols_vector}
            if isinstance(row["vibes"], list):
                row["vibes"] = " | ".join(row["vibes"])
            if isinstance(row["embedding_vector"], list):
                row["embedding_vector"] = json.dumps(row["embedding_vector"])
            w.writerow(row)


def sincronizar_banco_vetorial() -> List[Dict[str, Any]]:
    """
    Lê todos os locais aprovados no 2FA, gera os vetores (embeddings de 3.072 dimensões)
    para aqueles que ainda não têm vetor e salva no arquivo do Banco de Dados Vetorial (JSON e CSV).
    """
    env = load_env()
    gem_key = env.get("GEMINI_API_KEY", "")

    aprovados = load_json_list(BANCO_APROVADO_FILE)
    banco_vetorial_atual = load_json_list(VECTOR_DB_FILE)
    mapa_vetores_existentes = {
        str(x.get("video_id")): x.get("embedding_vector")
        for x in banco_vetorial_atual
        if x.get("embedding_vector")
    }

    registros_vetorizados = []
    for item in aprovados:
        vid = str(item.get("video_id"))
        doc_texto = montar_texto_para_vetorizacao(item)
        vetor = mapa_vetores_existentes.get(vid)

        if not vetor:
            vetor = gerar_embedding_gemini(doc_texto, gem_key)

        registro = {
            **item,
            "documento_indexado": doc_texto,
            "modelo_embedding": "models/gemini-embedding-001",
            "dimensoes_vetor": len(vetor) if vetor else 0,
            "embedding_vector": vetor or [],
        }
        registros_vetorizados.append(registro)

    save_json_list(VECTOR_DB_FILE, registros_vetorizados)
    exportar_csvs(registros_vetorizados)
    return registros_vetorizados


def buscar_no_banco_vetorial(pergunta_usuario: str, top_k: int = 3) -> List[Tuple[float, Dict[str, Any]]]:
    """
    Transforma a frase do usuário em um vetor de 3.072 números e calcula a
    Similaridade de Cosseno contra todos os lugares do Banco de Dados Vetorial.
    """
    env = load_env()
    gem_key = env.get("GEMINI_API_KEY", "")
    banco = load_json_list(VECTOR_DB_FILE)
    if not banco:
        banco = sincronizar_banco_vetorial()

    vetor_pergunta = gerar_embedding_gemini(pergunta_usuario, gem_key)
    if not vetor_pergunta:
        return []

    resultados = []
    for item in banco:
        vetor_local = item.get("embedding_vector", [])
        if vetor_local:
            score = similaridade_cosseno(vetor_pergunta, vetor_local)
            resultados.append((score, item))

    resultados.sort(key=lambda x: x[0], reverse=True)
    return resultados[:top_k]


def imprimir_banco_vetorial_no_terminal() -> None:
    """
    Exibe o Banco de Dados Vetorial diretamente no Terminal (CLI), mostrando:
    1. A tabela de locais aprovados no 2FA
    2. A amostra real do vetor matemático de 3.072 dimensões de cada local
    3. Uma simulação ao vivo de Busca Vetorial Semântica (RAG)
    """
    banco = sincronizar_banco_vetorial()

    print("\n" + "=" * 88)
    print("BANCO DE DADOS VETORIAL (2FA + EMBEDDINGS) — VISÃO DIRETA NO TERMINAL")
    print("=" * 88)
    print(f"Arquivo físico onde fica salvo: {VECTOR_DB_FILE}")
    print(f"Modelo de Vetorização: Google models/gemini-embedding-001")
    print(f"Total de documentos (lugares aprovados no 2FA): {len(banco)}")
    print("-" * 88)

    for idx, item in enumerate(banco, 1):
        vetor = item.get("embedding_vector", [])
        amostra_vetor = [round(v, 5) for v in vetor[:6]]
        vibes_fmt = ", ".join(item.get("vibes", []))
        print(f"\n[{idx}] {item.get('nome')} ({item.get('regiao_administrativa')})")
        print(f"    • Tipo de Rolê (Fator 1): {item.get('tipo_de_role')}")
        print(f"    • Vibes (Fator 1)       : {vibes_fmt}")
        print(f"    • Endereço (Fator 2)    : {item.get('endereco')}")
        print(f"    • Faixa Preço (Fator 2) : {item.get('faixa_de_preco')} (Média R$ {item.get('custo_medio_rs')})")
        print(f"    • Link TikTok Guardado  : {item.get('tiktok_url')}")
        print(f"    • Vetor ({item.get('dimensoes_vetor')} números) : {amostra_vetor} ... (mais {max(0, len(vetor)-6)} coordenadas)")

    print("\n" + "=" * 88)
    print("TESTE DE BUSCA VETORIAL POR SIGNIFICADO (SEM USAR PALAVRAS EXATAS)")
    print("=" * 88)

    perguntas_teste = [
        "Quero levar as crianças pequenas para ver luzes e passear em família gastando bem pouquinho",
        "Tô com muita fome, quero comer um lanche artesanal caprichado com carne e queijo",
        "Quero tomar um sorvete ou doce zero açúcar num lugar tranquilo na Asa Sul",
    ]

    for p in perguntas_teste:
        print(f"\nPergunta do Usuário: \"{p}\"")
        ranking = buscar_no_banco_vetorial(p, top_k=2)
        for pos, (score, loc) in enumerate(ranking, 1):
            seta = "[TOP 1] MATCH #1" if pos == 1 else "   Match #2"
            print(
                f"   {seta} -> Score Vetorial: {score:.4f} | {loc['nome']} "
                f"({loc['tipo_de_role']} em {loc['regiao_administrativa']} - R$ {loc['custo_medio_rs']})"
            )
    print("\n" + "=" * 88 + "\n")


if __name__ == "__main__":
    imprimir_banco_vetorial_no_terminal()
