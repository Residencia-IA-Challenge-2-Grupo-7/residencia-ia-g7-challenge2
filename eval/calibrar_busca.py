"""Compara a busca por palavras, a vetorial e a híbrida, sem chamar nenhum LLM (só embeddings da pergunta).

Para cada caso do golden, mostra em que posição o lugar do gabarito aparece em cada busca e a maior similaridade.
Para perguntas fora do tema da base, mostra a maior similaridade: é o que calibra o limiar do guardrail 1b.
Precisa da OPENROUTER_API_KEY (custo desprezível: um embedding por pergunta).

    PYTHONPATH=. python eval/calibrar_busca.py eval/resultados/calibracao-busca-<data>.json
"""
import json
import sys
import unicodedata

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")
from src.rag import busca_vetorial  # noqa: E402
from src.rag.comparador_ab import carregar_golden  # noqa: E402
from src.telemetria.telemetria import (calcular_similaridade_leticia, carregar_base_oficial_leticia,  # noqa: E402
                                       fundir_rankings)

# Pedidos que a base não atende (fora do tema), usados em 10/11 para o limiar da busca por palavras, e outros
FORA_DO_TEMA = [
    "oficina mecânica perto de mim",
    "boliche para ir com amigos",
    "museu de arte com exposição nova",
    "academia com personal trainer",
    "dentista que atende sábado",
    "loja de roupa de festa barata",
    "pet shop com banho e tosa",
    "curso de inglês à noite",
]


def norm(s):
    return unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()


base = carregar_base_oficial_leticia()
por_id = {b["id"]: b for b in base}


def rankings(pergunta):
    lex = sorted(base, key=lambda b: -calcular_similaridade_leticia(pergunta, b))
    lex_ids = [b["id"] for b in lex]
    cos, _ = busca_vetorial.similaridades(pergunta)
    vet_ids = sorted(cos, key=lambda i: -cos[i])
    hib_ids = fundir_rankings([lex_ids, vet_ids])
    return lex_ids, vet_ids, hib_ids, cos, calcular_similaridade_leticia(pergunta, lex[0])


def posicao(ids, gabarito):
    alvos = {norm(g) for g in gabarito}
    for n, i in enumerate(ids, 1):
        if norm(por_id[i]["nome"]) in alvos:
            return n
    return None


saida = {"golden": [], "fora_do_tema": []}
print("caso       pos léx  pos vet  pos híb  | máx léx  máx cos")
for caso in carregar_golden():
    if not caso["locais_gabarito"]:
        continue
    lex, vet, hib, cos, max_lex = rankings(caso["pergunta"])
    linha = {"id": caso["id"], "gabarito": caso["locais_gabarito"],
             "posicao_lexica": posicao(lex, caso["locais_gabarito"]),
             "posicao_vetorial": posicao(vet, caso["locais_gabarito"]),
             "posicao_hibrida": posicao(hib, caso["locais_gabarito"]),
             "max_lexica": max_lex, "max_cosseno": max(cos.values()),
             "top3_vetorial": [por_id[i]["nome"] for i in vet[:3]]}
    saida["golden"].append(linha)
    print(f"{caso['id']}  {linha['posicao_lexica']!s:>7}  {linha['posicao_vetorial']!s:>7}  "
          f"{linha['posicao_hibrida']!s:>7}  |  {max_lex:.2f}     {linha['max_cosseno']:.3f}   {linha['top3_vetorial']}")

print("\nfora do tema                                 máx léx  máx cos")
for pergunta in FORA_DO_TEMA:
    _, vet, _, cos, max_lex = rankings(pergunta)
    saida["fora_do_tema"].append({"pergunta": pergunta, "max_lexica": max_lex, "max_cosseno": max(cos.values()),
                                  "top1_vetorial": por_id[vet[0]]["nome"]})
    print(f"{pergunta:44} {max_lex:.2f}     {max(cos.values()):.3f}   {por_id[vet[0]]['nome']}")

with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(saida, f, ensure_ascii=False, indent=1)
