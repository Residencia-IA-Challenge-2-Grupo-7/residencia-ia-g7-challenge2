import json
import sys
import urllib.request
from typing import Any, Dict, List, Tuple

from banco_vetorial import (
    SSL_CTX,
    VECTOR_DB_FILE,
    buscar_no_banco_vetorial,
    sincronizar_banco_vetorial,
)
from coletor_tiktok_2fa import load_env


def gerar_resposta_fundamentada_rag(
    consulta: str, chunks_recuperados: List[Tuple[float, Dict[str, Any]]]
) -> str:
    """
    Etapa de Geração Aumentada por Recuperação (RAG - Grounded Generation):
    Envia a consulta do usuário + os Chunks recuperados do Banco Vetorial para o LLM,
    exigindo resposta 100% fundamentada nos documentos-fonte e citando os IDs/links.
    """
    env = load_env()
    gem_key = env.get("GEMINI_API_KEY", "")
    groq_key = env.get("GROQ_API_KEY", "")

    contexto_blocos = []
    for idx, (score, doc) in enumerate(chunks_recuperados, 1):
        contexto_blocos.append(
            f"[FONTE #{idx} | ID: {doc.get('id')} | Score Cosseno: {score:.4f}]\n"
            f"- Nome: {doc.get('nome')}\n"
            f"- Tipo de Rolê: {doc.get('tipo_de_role')}\n"
            f"- Vibes: {', '.join(doc.get('vibes', []))}\n"
            f"- Kid Friendly: {'Sim' if doc.get('kid_friendly') else 'Não'} ({doc.get('evidencia_kid_friendly', '')})\n"
            f"- Endereço Confirmado (Fator 2): {doc.get('endereco')} ({doc.get('regiao_administrativa')}) | GPS: ({doc.get('lat')}, {doc.get('lng')})\n"
            f"- Faixa de Preço (Fator 2): {doc.get('faixa_de_preco')} — Custo Médio: R$ {doc.get('custo_medio_rs')}\n"
            f"- Resumo Cultural: {doc.get('resumo_sensorial')}\n"
            f"- Trecho Transcrição Áudio (Whisper): \"{doc.get('transcricao_audio_whisper', '')[:350]}\"\n"
            f"- Link Fonte TikTok: {doc.get('tiktok_url')}\n"
        )

    contexto_str = "\n".join(contexto_blocos)

    prompt = (
        "Você é o assistente do Orquestrador de Rolês de Brasília (Protótipo de RAG).\n"
        "Responda à consulta do usuário utilizando EXCLUSIVAMENTE as informações contidas nos CHUNKS RECUPERADOS abaixo.\n"
        "Regras obrigatórias de fundamentação (Grounding):\n"
        "1. Não invente informações fora dos chunks recuperados.\n"
        "2. Cite explicitamente no texto qual fonte está usando (ex: [FONTE #1 - Nome do Local]).\n"
        "3. Mencione o endereço/região administrativa, a faixa de preço (em R$), as vibes e por que o local atende ao pedido.\n\n"
        f"=== CONSULTA DO USUÁRIO ===\n{consulta}\n\n"
        f"=== CHUNKS RECUPERADOS DO BANCO VETORIAL ===\n{contexto_str}\n\n"
        "=== RESPOSTA FUNDAMENTADA ==="
    )

    # 1. Tenta Gemini (gemini-3-flash-preview)
    if gem_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={gem_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception:
            pass

    # 2. Fallback Groq (qwen/qwen3.8-27b ou openai/gpt-oss-120b)
    if groq_key:
        for model_name in ("qwen/qwen3.8-27b", "openai/gpt-oss-120b"):
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {groq_key}",
                        "User-Agent": "Mozilla/5.0",
                    },
                )
                with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    texto = data["choices"][0]["message"]["content"].strip()
                    if "</think>" in texto:
                        texto = texto.split("</think>")[-1].strip()
                    return texto
            except Exception:
                continue

    # 3. Fallback determinístico caso esteja offline
    linhas = ["Com base nos documentos recuperados do Banco Vetorial, recomendamos:"]
    for idx, (score, doc) in enumerate(chunks_recuperados, 1):
        linhas.append(
            f"- [FONTE #{idx} - {doc.get('nome')}] ({doc.get('tipo_de_role')} em {doc.get('regiao_administrativa')}): "
            f"{doc.get('resumo_sensorial')} Endereço: {doc.get('endereco')}. "
            f"Faixa de preço: {doc.get('faixa_de_preco')} (média de R$ {doc.get('custo_medio_rs')}). "
            f"Fonte: {doc.get('tiktok_url')}"
        )
    return "\n".join(linhas)


def executar_demonstracao_rag(consultas: List[str], top_k: int = 3) -> None:
    """
    Executa a demonstração completa exigida no entregável da Residência (UnB / Eldorado):
    1. Consulta submetida ao sistema
    2. Recuperação dos chunks/documentos mais relevantes (com score vetorial)
    3. Resposta fundamentada no conteúdo recuperado (Grounded Generation)
    4. Evidência das fontes utilizadas na resposta (Rastreabilidade)
    """
    banco = sincronizar_banco_vetorial()
    print("=" * 95)
    print("ENTREGÁVEL: BASE DE CONHECIMENTO CURADA (2FA) + PROTÓTIPO DE RAG")
    print("   RES IA ELD UNB - Turma 2 | Grupo 7 — Orquestrador de Rolês")
    print("=" * 95)
    print(f"Base de Conhecimento Curada : {len(banco)} documentos-fonte aprovados no 2FA (Mínimo exigido: 20)")
    print("Estratégia de Chunking      : Entity-Centric Semantic Chunking (1 chunk estruturado autocontido por rolê)")
    print("Estratégia de Embeddings    : Google models/gemini-embedding-001 (Vetores densos de 3.072 dimensões)")
    print(f"Banco Vetorial Persistido   : {VECTOR_DB_FILE.name} (Busca por Similaridade de Cosseno)")
    print("=" * 95)

    for num_q, consulta in enumerate(consultas, 1):
        print(f"\n\n{'#' * 95}")
        print(f"CASO DE DEMONSTRAÇÃO #{num_q}")
        print(f"{'#' * 95}")

        # 1. Consulta submetida ao sistema
        print("\n[1] CONSULTA SUBMETIDA AO SISTEMA:")
        print(f"    \"{consulta}\"")

        # 2. Recuperação dos chunks mais relevantes
        resultados = buscar_no_banco_vetorial(consulta, top_k=top_k)
        print(f"\n[2] RECUPERAÇÃO DOS CHUNKS MAIS RELEVANTES (TOP-{top_k} POR SIMILARIDADE DE COSSENO):")
        for idx, (score, doc) in enumerate(resultados, 1):
            print(f"\n    - CHUNK RECUPERADO #{idx} | Score Vetorial (Cosseno): {score:.4f} | ID: {doc.get('id')}")
            print(f"       • Documento Indexado (Chunk): \"{doc.get('documento_indexado', '')[:260]}...\"")

        # 3. Resposta fundamentada no conteúdo recuperado
        print("\n[3] RESPOSTA FUNDAMENTADA NO CONTEÚDO RECUPERADO (RAG GENERATION):")
        resposta_rag = gerar_resposta_fundamentada_rag(consulta, resultados)
        for linha in resposta_rag.splitlines():
            print(f"    {linha}")

        # 4. Evidência das fontes utilizadas na resposta
        print("\n[4] EVIDÊNCIA E RASTREABILIDADE DAS FONTES UTILIZADAS:")
        for idx, (score, doc) in enumerate(resultados, 1):
            print(f"    [OK] [FONTE #{idx}] {doc.get('nome')} ({doc.get('tipo_de_role')})")
            print(f"       ├─ ID do Documento : {doc.get('id')} (Publicado em: {doc.get('data_publicacao')})")
            print(f"       ├─ Score Similaridade: {score:.4f} (Vetor de {doc.get('dimensoes_vetor')} dimensões)")
            print(f"       ├─ Localização (Fator 2): {doc.get('endereco')} | RA: {doc.get('regiao_administrativa')} | GPS: ({doc.get('lat')}, {doc.get('lng')})")
            print(f"       ├─ Preço Validado (Fator 2): {doc.get('faixa_de_preco')} (Média R$ {doc.get('custo_medio_rs')})")
            print(f"       ├─ Evidência Áudio Whisper : \"{doc.get('transcricao_audio_whisper', '')[:160]}...\"")
            print(f"       └─ Link Original (TikTok)  : {doc.get('tiktok_url')}")

    print("\n" + "=" * 95)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        perguntas = [" ".join(sys.argv[1:])]
    else:
        perguntas = [
            "Quero levar meus filhos pequenos num passeio iluminado ou parque tranquilo gastando até 30 reais por pessoa",
            "Onde consigo comer um hambúrguer artesanal caprichado ou rodízio num ambiente animado para ir com amigos?",
            "Procuro uma confeitaria ou gelateria com opções zero açúcar ou saudáveis na Asa Sul para conversar com calma",
        ]
    executar_demonstracao_rag(perguntas, top_k=3)
