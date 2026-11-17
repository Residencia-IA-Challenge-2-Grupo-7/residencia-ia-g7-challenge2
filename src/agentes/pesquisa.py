"""Agente 1 — Pesquisa (LLM + ferramenta de busca).

Duas etapas, cada uma com uma chamada ao LLM e o prompt `prompts/pesquisa.md`:

1. **planejar:** a partir do perfil anônimo do grupo (e do pedido da Validação, na volta), escreve de 1 a 3
   consultas; o código roda `ferramentas.buscar` em cada uma;
2. **selecionar:** lê os documentos trazidos e escolhe de 8 a 10 candidatos, cada um com motivo e trecho literal,
   que o código confere (`ferramentas.conferir_trecho`).

Sem chave da OpenRouter, ou se o LLM falhar, as consultas e a seleção saem por regras (reserva), para o grafo nunca
parar (RNF-15).

Interface da issue #70:

- `buscar_lugares_rag(query, categorias)`: a ferramenta determinística, sobre a base oficial de 93 lugares (ADR 0008)
  e a busca do RAG (léxica ou vetorial, ADR 0012);
- `executar_agente_pesquisa(perfil_grupo, feedback_validacao=None)`: o agente inteiro, com a saída
  `{fonte_id, nome, tipo, motivo, trecho_citado}` por candidato.

Por que o LLM não chama a ferramenta por *tool calling* nativo: ele escreve até 3 consultas numa resposta só, com
JSON Schema estrito, e o código as executa. É a mesma ferramenta com uma chamada de LLM a menos por rodada (RNF-14)
e sem o modelo decidir quantas vezes buscar.

A entrada é validada: o perfil do grupo pelo esquema `PreferenciasGrupo` e o retorno da Validação pelo
`PedidoNovaBusca`, que só tem contagens. Chave a mais (um teto, um texto livre) é erro antes de chegar ao LLM (RNF-02).
"""
from __future__ import annotations

import json

from src.agentes import ferramentas
from src.agentes.contratos import Candidato, Consulta, SaidaPlanejar, SaidaSelecionar, TipoRole, esquema_estrito
from src.agentes.estado import PedidoNovaBusca, PreferenciasGrupo
from src.agentes.llm import ClienteLLM, ErroLLM, embrulhar, prompt
from src.interpretador.lugares import ras_validas
from src.salas import integracoes as integ

PARA_TIPO_ROLE = {"Bar / Boteco / Pub": "comer_beber", "Restaurante / Gastronomia": "comer_beber",
                  "Cafeteria / Doceria": "comer_beber", "Ao Ar Livre / Parque": "ar_livre_gratuito",
                  "Experiência / Evento": "local_evento"}
CATEGORIAS = frozenset(TipoRole.__args__)  # comer_beber, ar_livre_gratuito, local_evento
MAX_DOCUMENTOS = 20
MAX_CANDIDATOS = 10
GRUPO_VAZIO = {"tamanho": 1, "tipos": [], "tipos_pedidos": {}, "vibes": [], "evitar": [], "restricoes": [],
               "trechos_pedido": [], "janela": None}


def _consultas_por_regras(grupo: dict, pedido: dict | None) -> list[Consulta]:
    tipos = sorted({PARA_TIPO_ROLE[t] for t in grupo["tipos"] if t in PARA_TIPO_ROLE})
    vibes = " ".join(v.split(" / ")[0].lower() for v in grupo["vibes"][:3])
    nomes_tipos = " ".join(t.split(" / ")[0].lower() for t in grupo["tipos"][:3])
    texto = (f"{nomes_tipos} {vibes}".strip() or "rolê com amigos")
    consultas = [Consulta(texto=texto, tipos_role=tipos, exigir=grupo["restricoes"], ras=[])]
    if pedido and pedido.get("vetos", {}).get("orcamento"):
        consultas.append(Consulta(texto="lugar barato baratinho", tipos_role=[], exigir=grupo["restricoes"], ras=[]))
    if pedido and pedido.get("vetos", {}).get("horario"):
        consultas.append(Consulta(texto=f"{vibes} aberto todos os dias", tipos_role=[], exigir=[], ras=[]))
    return consultas[:3]


def _mensagem(etapa: str, grupo: dict, pedido: dict | None, extra: str = "") -> str:
    partes = [f"Etapa: {etapa}", embrulhar("perfil_anonimo_do_grupo", grupo)]
    if pedido:  # gerado por código (contagens), não é dado de usuário
        partes.append("Pedido da Validação (gerado pelo sistema): " + json.dumps(pedido, ensure_ascii=False))
    if extra:
        partes.append(extra)
    return "\n\n".join(partes)


def pesquisar(grupo: dict, pedido: dict | None, lugares: list[dict], cliente: ClienteLLM, *,
              busca: str = "lexica", excluir: set[str] = frozenset()) -> dict:
    """-> {candidatos, observacao, consultas, usou_llm, descartados, buscas, documentos}. `grupo` e `pedido` são
    validados (PreferenciasGrupo e PedidoNovaBusca): nada além de perfil anônimo e contagens vai ao LLM."""
    grupo = PreferenciasGrupo.model_validate(grupo).model_dump()
    pedido = PedidoNovaBusca.model_validate(pedido).model_dump() if pedido else None
    sistema = prompt("pesquisa")
    usou_llm = False
    # 1. planejar
    consultas: list[Consulta] = []
    if cliente.disponivel:
        try:
            bruto = cliente.json("pesquisa_planejar", sistema, _mensagem("planejar", grupo, pedido),
                                 esquema_estrito(SaidaPlanejar), max_tokens=600)
            validas = set(ras_validas())
            consultas = [c.model_copy(update={"ras": [r for r in c.ras if r in validas]})
                         for c in SaidaPlanejar.model_validate(bruto).consultas]
            usou_llm = True
        except (ErroLLM, ValueError):
            consultas = []
    consultas = consultas or _consultas_por_regras(grupo, pedido)

    # 2. ferramenta de busca
    achados: dict[str, dict] = {}
    buscas = []
    for c in consultas:
        itens, meta = ferramentas.buscar(c, lugares, busca=busca)
        buscas.append({"consulta": c.texto, "tipos_role": c.tipos_role, **meta, "trouxe": len(itens)})
        for it in itens:
            if it["id"] not in excluir and it["pontuacao"] > achados.get(it["id"], {}).get("pontuacao", -1):
                achados[it["id"]] = it
    documentos = sorted(achados.values(), key=lambda d: -d["pontuacao"])[:MAX_DOCUMENTOS]
    por_id = {l["id"]: l for l in lugares}

    # 3. selecionar
    candidatos: list[Candidato] = []
    observacao = ""
    descartados = 0
    if cliente.disponivel and documentos:
        docs_llm = [{k: v for k, v in d.items() if k != "pontuacao"} for d in documentos]
        try:
            bruto = cliente.json("pesquisa_selecionar", sistema,
                                 _mensagem("selecionar", grupo, pedido, embrulhar("documentos_da_base", docs_llm)),
                                 esquema_estrito(SaidaSelecionar), max_tokens=1800)
            saida = SaidaSelecionar.model_validate(bruto)
            ids_docs = {d["id"] for d in documentos}
            vistos = set()
            for c in saida.candidatos:
                if c.id in ids_docs and c.id not in vistos and ferramentas.conferir_trecho(c.trecho, por_id[c.id]):
                    candidatos.append(c)
                    vistos.add(c.id)
                else:
                    descartados += 1
            observacao = saida.observacao
            usou_llm = True
        except (ErroLLM, ValueError):
            candidatos = []
    if len(candidatos) < 3:  # reserva: os mais bem pontuados da busca
        ja = {c.id for c in candidatos}
        for d in documentos:
            if len(candidatos) >= 8:
                break
            if d["id"] not in ja:
                tipo = d["tipo"].split(" / ")[0].lower() or "lugar"
                candidatos.append(Candidato(id=d["id"], trecho=d["nome"],
                                            motivo=f"{tipo.capitalize()} entre os mais próximos do pedido do grupo."))
    return {"candidatos": [c.model_dump() for c in candidatos[:MAX_CANDIDATOS]], "observacao": observacao,
            "consultas": [c.model_dump() for c in consultas], "usou_llm": usou_llm, "descartados": descartados,
            "buscas": buscas, "documentos": {d["id"]: d for d in documentos}}


# ------------------------------------------------------------------ interface da issue #70

def _categorias(categorias) -> list[str]:
    """Aceita as categorias da ferramenta (comer_beber...) ou os tipos da base ("Bar / Boteco / Pub"...)."""
    saida = []
    for c in categorias or []:
        cat = PARA_TIPO_ROLE.get(c, c)
        if cat not in CATEGORIAS:
            raise ValueError(f"categoria desconhecida: {c!r}; use {sorted(CATEGORIAS)} ou um tipo da base")
        if cat not in saida:
            saida.append(cat)
    return saida


def buscar_lugares_rag(query: str, categorias: list[str] | None = None, *, exigir: list[str] | None = None,
                       ras: list[str] | None = None, lugares: list[dict] | None = None, busca: str = "lexica",
                       k: int = 12) -> list[dict]:
    """Ferramenta determinística da Pesquisa: os `k` lugares da base oficial que mais combinam com `query`, já no
    formato que um LLM pode ler (id, nome, tipo, região do lugar, vibes, descrição e pontuação; sem preço, horário
    nem endereço). `categorias`: comer_beber, ar_livre_gratuito, local_evento (vazio = todas)."""
    consulta = Consulta(texto=query, tipos_role=_categorias(categorias), exigir=list(exigir or []),
                        ras=list(ras or []))
    base = list(lugares) if lugares is not None else list(integ.carregar_lugares())
    itens, _ = ferramentas.buscar(consulta, base, busca=busca, k=k)
    return itens


def executar_agente_pesquisa(perfil_grupo: dict, feedback_validacao: dict | None = None, *,
                             cliente: ClienteLLM | None = None, lugares: list[dict] | None = None,
                             busca: str = "lexica", excluir: set[str] | frozenset[str] = frozenset()) -> list[dict]:
    """O agente de Pesquisa (issue #70): de 8 a 10 candidatos da base, cada um com o trecho literal do documento
    que sustenta o motivo, conferido em código.

    `perfil_grupo`: o perfil anônimo do grupo (`PreferenciasGrupo`; campos ausentes ficam vazios).
    `feedback_validacao`: na volta da Validação, `{faltam, vetos: {motivo: contagem}, ja_vistos}`.
    `excluir`: ids que já foram julgados nas voltas anteriores. Sem `cliente`, usa a OpenRouter do .env; sem chave,
    tudo sai por regras."""
    cliente = cliente or ClienteLLM()
    base = list(lugares) if lugares is not None else list(integ.carregar_lugares())
    r = pesquisar({**GRUPO_VAZIO, **perfil_grupo}, feedback_validacao, base, cliente, busca=busca,
                  excluir=set(excluir))
    docs = r["documentos"]
    return [{"fonte_id": c["id"], "nome": docs[c["id"]]["nome"], "tipo": docs[c["id"]]["tipo"],
             "motivo": c["motivo"], "trecho_citado": c["trecho"]} for c in r["candidatos"]]
