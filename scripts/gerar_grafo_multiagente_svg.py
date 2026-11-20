"""Gera o diagrama do grafo multiagente em SVG (issue #75).

O desenho segue as arestas do grafo compilado em `src/agentes/grafo.py` (as mesmas que o LangGraph desenha em
`docs/entregas/semana-04/grafo_agentes.mmd`):

    __start__ -.-> no_pessoal (um por membro)      no_pessoal --> no_consolidar_grupo
    no_consolidar_grupo -.-> no_pesquisa            no_consolidar_grupo -.-> no_finalizar
    no_pesquisa --> no_logistica --> no_validacao
    no_validacao -.-> no_pesquisa | no_comunicacao | no_finalizar
    no_comunicacao --> no_validacao_textos
    no_validacao_textos -.-> no_comunicacao | no_finalizar
    no_finalizar --> __end__

Código de cores: azul = nó com LLM, verde = código, roxo = híbrido (código + juiz LLM), laranja = cofre do
servidor (fora do estado do grafo, RNF-02), âmbar = decisão (aresta condicional).

    python scripts/gerar_grafo_multiagente_svg.py   # grava docs/arquitetura/img/grafo_multiagente.svg
"""
from __future__ import annotations

from html import escape
from pathlib import Path

SAIDA = Path("docs/arquitetura/img/grafo_multiagente.svg")

LARGURA = 1300
CX = 580                      # eixo do fluxo principal
CARD_X, CARD_W = 330, 500     # coluna dos nós
COFRE_X, COFRE_W = 900, 340   # coluna do cofre
TRILHO_X = 1272               # trilho das saídas direto para o fim

ESTILOS = {
    "llm": dict(fill="#082f49", stroke="#0ea5e9", badge="#0284c7", badge_txt="#e0f2fe", tag="#38bdf8",
                txt="#bae6fd", foot="#0c4a6e", foot_txt="#7dd3fc"),
    "code": dict(fill="#064e3b", stroke="#10b981", badge="#047857", badge_txt="#d1fae5", tag="#6ee7b7",
                 txt="#a7f3d0", foot="#065f46", foot_txt="#6ee7b7"),
    "hybrid": dict(fill="#3b0764", stroke="#a855f7", badge="#7e22ce", badge_txt="#fae8ff", tag="#d8b4fe",
                   txt="#e9d5ff", foot="#581c87", foot_txt="#f5d0fe"),
}

CORES_SETA = {"cyan": "#38bdf8", "green": "#4ade80", "purple": "#c084fc", "amber": "#fbbf24",
              "orange": "#fb923c", "red": "#f87171", "slate": "#94a3b8"}


def _t(texto: str) -> str:
    return escape(texto, quote=False)


def _largura_texto(texto: str, tamanho: float) -> float:
    return len(texto) * tamanho * 0.56


# ------------------------------------------------------------------ peças

def _card(y: int, tipo: str, selo: str, etiqueta: str, titulo: str, linhas: list[str], saida: str,
          empilhado: bool = False) -> tuple[str, int]:
    """Cartão de um nó. Devolve (svg, altura)."""
    e = ESTILOS[tipo]
    altura = 78 + 18 * len(linhas) + 34
    partes = []
    if empilhado:  # o Agente Pessoal roda uma vez por membro
        for d in (14, 7):
            partes.append(f'<rect x="{CARD_X + d}" y="{y + d}" width="{CARD_W}" height="{altura}" rx="14" '
                          f'fill="{e["fill"]}" stroke="{e["stroke"]}" stroke-width="1.5" opacity="0.55"/>')
    selo_w = round(_largura_texto(selo, 11) * 1.12 + 16)   # caixa alta em negrito ocupa mais
    partes += [
        f'<g transform="translate({CARD_X}, {y})">',
        f'  <rect x="0" y="0" width="{CARD_W}" height="{altura}" rx="14" fill="{e["fill"]}" stroke="{e["stroke"]}" '
        f'stroke-width="2" filter="url(#cardShadow)"/>',
        f'  <rect x="18" y="16" width="{selo_w}" height="22" rx="4" fill="{e["badge"]}"/>',
        f'  <text x="26" y="32" font-size="11" font-weight="700" fill="{e["badge_txt"]}">{_t(selo)}</text>',
        f'  <text x="{18 + selo_w + 12}" y="32" font-size="11" font-weight="600" fill="{e["tag"]}">{_t(etiqueta)}</text>',
        f'  <text x="18" y="64" font-size="15" font-weight="700" fill="#ffffff">{_t(titulo)}</text>',
    ]
    for i, linha in enumerate(linhas):
        recuo = 30 if linha.startswith("  ") else 18
        partes.append(f'  <text x="{recuo}" y="{88 + 18 * i}" font-size="12" fill="{e["txt"]}">{_t(linha.strip())}</text>')
    yf = altura - 34
    partes += [
        f'  <rect x="18" y="{yf}" width="{CARD_W - 36}" height="22" rx="4" fill="{e["foot"]}"/>',
        f'  <text x="26" y="{yf + 15}" font-size="11" font-weight="600" fill="{e["foot_txt"]}">{_t(saida)}</text>',
        '</g>',
    ]
    return "\n  ".join(partes), altura


def _pilula(y: int, texto: str, cor: str, borda: str) -> tuple[str, int]:
    w = round(_largura_texto(texto, 13) + 48)
    x = CX - w // 2
    return (f'<rect x="{x}" y="{y}" width="{w}" height="44" rx="22" fill="{cor}" stroke="{borda}" stroke-width="2" '
            f'filter="url(#cardShadow)"/>\n  <text x="{CX}" y="{y + 27}" font-size="13" font-weight="700" '
            f'fill="#e0e7ff" text-anchor="middle">{_t(texto)}</text>'), 44


def _losango(y: int, meia_l: int, meia_a: int, linhas: list[str]) -> tuple[str, int]:
    cy = y + meia_a
    pontos = f"{CX},{y} {CX + meia_l},{cy} {CX},{y + 2 * meia_a} {CX - meia_l},{cy}"
    partes = [f'<polygon points="{pontos}" fill="#78350f" stroke="#f59e0b" stroke-width="2" filter="url(#cardShadow)"/>']
    y0 = cy - 9 * (len(linhas) - 1)
    for i, linha in enumerate(linhas):
        peso, tam, cor = ("700", 13, "#fef3c7") if i == 0 else ("600", 11, "#fde68a")
        partes.append(f'<text x="{CX}" y="{y0 + 18 * i + 4}" font-size="{tam}" font-weight="{peso}" fill="{cor}" '
                      f'text-anchor="middle">{_t(linha)}</text>')
    return "\n  ".join(partes), 2 * meia_a


def _seta(pontos: list[tuple[float, float]], cor: str, tracejado: bool = False, ponta: bool = True,
          largura: float = 2.5) -> str:
    d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in pontos)
    extra = ' stroke-dasharray="6 4"' if tracejado else ""
    fim = f' marker-end="url(#seta_{cor})"' if ponta else ""
    return f'<path d="{d}" fill="none" stroke="{CORES_SETA[cor]}" stroke-width="{largura}"{extra}{fim}/>'


def _rotulo(x: float, y: float, linhas: list[str] | str, cor: str, ancora: str = "middle",
            fundo: str = "#0f172a") -> str:
    """Rótulo de aresta com fundo opaco, para não brigar com as linhas que cruzam."""
    linhas = [linhas] if isinstance(linhas, str) else linhas
    w = max(_largura_texto(l, 11) for l in linhas) + 14
    h = 16 * len(linhas) + 6
    x0 = {"middle": x - w / 2, "start": x - 7, "end": x - w + 7}[ancora]
    partes = [f'<rect x="{x0:g}" y="{y - 14:g}" width="{w:g}" height="{h}" rx="4" fill="{fundo}" '
              f'stroke="{CORES_SETA[cor]}" stroke-width="1" stroke-opacity="0.6"/>']
    for i, linha in enumerate(linhas):
        partes.append(f'<text x="{x:g}" y="{y + 16 * i:g}" font-size="11" font-weight="600" '
                      f'fill="{CORES_SETA[cor]}" text-anchor="{ancora}">{_t(linha)}</text>')
    return "\n  ".join(partes)


def _defs() -> str:
    marcadores = "\n".join(
        f'    <marker id="seta_{nome}" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">'
        f'<path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{cor}"/></marker>'
        for nome, cor in CORES_SETA.items())
    return f"""  <defs>
    <linearGradient id="headerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#818cf8"/>
    </linearGradient>
    <linearGradient id="telemetryGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e293b"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </linearGradient>
    <filter id="cardShadow" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#000000" flood-opacity="0.45"/>
    </filter>
{marcadores}
  </defs>"""


def _cabecalho() -> str:
    legenda = [("#38bdf8", "#0284c7", "Nó com LLM"), ("#4ade80", "#16a34a", "Código (RNF-04)"),
               ("#c084fc", "#9333ea", "Híbrido: código + juiz LLM"), ("#fb923c", "#ea580c", "Cofre do servidor (RNF-02)"),
               ("#fbbf24", "#d97706", "Aresta condicional")]
    partes, x = [], 30
    for cor, borda, texto in legenda:
        w = round(_largura_texto(texto, 11.5) + 40)
        partes.append(f'<g transform="translate({x}, 76)"><rect x="0" y="0" width="{w}" height="24" rx="6" '
                      f'fill="#0f172a" stroke="{borda}" stroke-width="1.5"/><circle cx="13" cy="12" r="5" fill="{cor}"/>'
                      f'<text x="25" y="16" font-size="11.5" font-weight="600" fill="#e2e8f0">{_t(texto)}</text></g>')
        x += w + 10
    itens = "\n    ".join(partes)
    return f"""<g transform="translate(50, 30)">
    <rect x="0" y="0" width="1200" height="116" rx="16" fill="#1e293b" stroke="#334155" stroke-width="1.5" filter="url(#cardShadow)"/>
    <text x="30" y="40" font-size="24" font-weight="700" fill="url(#headerGrad)" letter-spacing="0.5">Arquitetura do Grafo Multiagente (LangGraph)</text>
    <text x="30" y="63" font-size="13" fill="#94a3b8">Grafo implementado em src/agentes/grafo.py, desenhado a partir das arestas do grafo compilado · Orquestrador de Rolês · Semana 4</text>
    {itens}
  </g>"""


def _cofre(y: int, altura: int) -> str:
    canais = [
        ("#fca5a5", "Canal 1 · orçamento", "teto individual → vetos da Validação"),
        ("#fdba74", "Canal 2 · restrições", "restrições duras → vetos da Validação"),
        ("#93c5fd", "Canal 4 · logística", "origem, janelas e transporte → Logística"),
    ]
    partes = [
        f'<g transform="translate({COFRE_X}, {y})">',
        f'  <rect x="0" y="0" width="{COFRE_W}" height="{altura}" rx="14" fill="#1c1917" stroke="#ea580c" '
        f'stroke-width="2" stroke-dasharray="6 4" filter="url(#cardShadow)"/>',
        '  <text x="18" y="30" font-size="13" font-weight="700" fill="#fb923c">🔒 COFRE DO SERVIDOR</text>',
        '  <text x="18" y="50" font-size="11" fill="#fdba74">fora do MultiAgentState (ADR 0015 e 0016)</text>',
    ]
    for i, (cor, nome, desc) in enumerate(canais):
        yy = 66 + 52 * i
        partes += [
            f'  <rect x="18" y="{yy}" width="{COFRE_W - 36}" height="42" rx="6" fill="#292524" stroke="{cor}" stroke-opacity="0.5"/>',
            f'  <text x="30" y="{yy + 17}" font-size="11.5" font-weight="700" fill="{cor}">{_t(nome)}</text>',
            f'  <text x="30" y="{yy + 33}" font-size="11" fill="#d6d3d1">{_t(desc)}</text>',
        ]
    notas = ["Só os nós de código leem o cofre.", "Não vai para o checkpoint, o Langfuse",
             "nem para um LLM (RNF-02).", "serializar_estado recusa o estado que",
             "tiver chave do cofre ou nome de membro.", "O nó de finalização lê lugares e",
             "trajetos daqui para os números do cartão."]
    for i, nota in enumerate(notas):
        partes.append(f'  <text x="18" y="{236 + 17 * i}" font-size="11" fill="#e7e5e4">{_t(nota)}</text>')
    partes.append("</g>")
    return "\n  ".join(partes)


def _telemetria(y: int) -> tuple[str, int]:
    linhas = [
        "• Um trace por execução (trace_url no estado). Um span por nó, com o nome da etapa: agente_pessoal, consolidar_grupo,",
        "  pesquisa, logistica, validacao, comunicacao, validacao_textos e finalizar. Entrada e saída escolhidas à mão, nunca o estado inteiro.",
        "• RNF-14: 5 s para responder na conversa e 60 s para gerar os planos (no demo da #74, o cenário de controle levou 24,6 s até os cartões).",
    ]
    textos = "\n      ".join(f'<text x="0" y="{46 + 20 * i}" font-size="12" fill="#cbd5e1">{_t(l)}</text>'
                           for i, l in enumerate(linhas))
    return f"""<g transform="translate(50, {y})">
    <rect x="0" y="0" width="1200" height="120" rx="14" fill="url(#telemetryGrad)" stroke="#334155" stroke-width="1.5" filter="url(#cardShadow)"/>
    <g transform="translate(25, 22)">
      <circle cx="8" cy="0" r="7" fill="#f43f5e"/>
      <text x="24" y="5" font-size="14" font-weight="700" fill="#fda4af">Observabilidade · Langfuse Cloud (v5.x)</text>
      {textos}
    </g>
  </g>""", 120


# ------------------------------------------------------------------ diagrama

def gerar_svg_multiagente() -> str:
    corpo: list[str] = []      # nós
    arestas: list[str] = []    # setas, desenhadas antes dos nós
    rotulos: list[str] = []    # rótulos, desenhados por cima de tudo

    # início
    y = 176
    svg, h = _pilula(y, "INÍCIO · sala com N membros confirmados (4 campos da Tela 2)", "#1e1b4b", "#818cf8")
    corpo.append(svg)
    inicio_fim = y + h

    # 0. Agente Pessoal, um por membro
    y_pessoal = inicio_fim + 56
    svg, h_pessoal = _card(
        y_pessoal, "code", "0. AGENTE PESSOAL ×N", "⚙️ Código (RNF-04)",
        "no_pessoal · um por membro, em paralelo (Send)",
        ["• Interpreta os 4 campos por regras (src/interpretador/campos.py, ADR 0009)",
         "• Junta o log pessoal do membro (store do LangGraph); o que ele escreveu agora vence",
         "• Separa 4 canais: 1, 2 e 4 vão para o cofre; só o canal 3 segue no grafo"],
        "Saída: membros_anonimos (PerfilAnonimoMembro, só o marcador m1..mN)", empilhado=True)
    corpo.append(svg)
    arestas.append(_seta([(CX, inicio_fim), (CX, y_pessoal)], "slate", tracejado=True))
    rotulos.append(_rotulo(CX + 14, inicio_fim + 32, "Send: um Agente Pessoal por membro", "slate", "start"))
    pessoal_fim = y_pessoal + h_pessoal + 14

    # Orquestrador: consolidação
    y_cons = pessoal_fim + 64
    svg, h_cons = _card(
        y_cons, "code", "ORQUESTRADOR", "⚙️ Código",
        "no_consolidar_grupo · junta os perfis anônimos",
        ["• Tipos e vibes contados (\"x de y\") e restrições somadas, sem dizer de quem são",
         "• Melhor janela comum, cruzada no cofre"],
        "Saída: preferencias_grupo")
    corpo.append(svg)
    arestas.append(_seta([(CX, pessoal_fim), (CX, y_cons)], "green"))
    rotulos.append(_rotulo(CX + 14, pessoal_fim + 36, "canal 3 · preferências (o único público)", "green", "start"))
    cons_fim = y_cons + h_cons

    # decisão 1: há janela comum?
    y_d1 = cons_fim + 46
    svg, h_d1 = _losango(y_d1, 130, 46, ["Há janela comum?", "(pelo menos 2 pessoas)"])
    corpo.append(svg)
    d1_meio = y_d1 + h_d1 // 2
    arestas.append(_seta([(CX, cons_fim), (CX, y_d1)], "green"))

    # 1. Pesquisa
    y_pesq = y_d1 + h_d1 + 56
    svg, h_pesq = _card(
        y_pesq, "llm", "1. AGENTE DE PESQUISA", "🤖 LLM: DeepSeek V4.1 Flash",
        "no_pesquisa · curador da cena do DF",
        ["• O LLM escreve até 3 consultas; o código executa buscar_lugares_rag",
         "  (sem tool calling nativo, decisão da #70)",
         "• Só a base curada de 93 lugares com 2FA no TikTok (ADR 0008)",
         "• 8 a 10 candidatos, cada motivo com trecho_citado conferido no documento",
         "• Não recebe teto, origem nem nome de ninguém (RNF-02)"],
        "Saída: candidatos_pesquisa, documentos, vistos")
    corpo.append(svg)
    arestas.append(_seta([(CX, y_d1 + h_d1), (CX, y_pesq)], "amber"))
    rotulos.append(_rotulo(CX + 14, y_d1 + h_d1 + 32, "sim", "amber", "start"))
    pesq_meio, pesq_fim = y_pesq + h_pesq // 2, y_pesq + h_pesq

    # 2. Logística
    y_log = pesq_fim + 64
    svg, h_log = _card(
        y_log, "code", "2. AGENTE DE LOGÍSTICA E JUSTIÇA", "⚙️ Código (RNF-04)",
        "no_logistica · trajeto de cada um, medido no cofre",
        ["• Meio mais barato que chega em até 75 min, para cada membro",
         "• Regra da Menor Miséria (ADR 0013): nota de justiça pelo pior trajeto",
         "• Pontuação: 45% aderência + 35% justiça + 20% horário",
         "• Trajeto de cada pessoa fica em Cofre.analises; o parecer só tem agregados"],
        "Saída: candidatos_avaliados (agregados, sem trajeto por pessoa)")
    corpo.append(svg)
    arestas.append(_seta([(CX, pesq_fim), (CX, y_log)], "cyan"))
    rotulos.append(_rotulo(CX + 14, pesq_fim + 36, "candidatos_pesquisa", "cyan", "start"))
    log_meio, log_fim = y_log + h_log // 2, y_log + h_log

    # 3. Validação
    y_val = log_fim + 64
    svg, h_val = _card(
        y_val, "hybrid", "3. AGENTE DE VALIDAÇÃO", "🛡️ Código + juiz LLM (opcional)",
        "no_validacao · vetos em código e convergência",
        ["• Vetos em código (RNF-04): horário, orçamento (teto de cada um), restrição,",
         "  encerrado e deslocamento acima de 75 min",
         "• Juiz, 1ª passagem (#72, opcional): derruba o candidato cujo motivo",
         "  contradiz o documento (GLM-5.3-Flash, ADR 0014)",
         "• Escolhe até 4 cartões na ordem do ranking"],
        "Saída: relatorio_validacao, candidatos_validados, pedido_nova_busca")
    corpo.append(svg)
    arestas.append(_seta([(CX, log_fim), (CX, y_val)], "green"))
    rotulos.append(_rotulo(CX + 14, log_fim + 36, "candidatos_avaliados", "green", "start"))
    val_meio, val_fim = y_val + h_val // 2, y_val + h_val

    # decisão 2: avaliar_convergencia
    y_d2 = val_fim + 50
    svg, h_d2 = _losango(y_d2, 160, 56, ["avaliar_convergencia", "3 ou mais validados?", "(máximo de 2 voltas)"])
    corpo.append(svg)
    d2_meio = y_d2 + h_d2 // 2
    arestas.append(_seta([(CX, val_fim), (CX, y_d2)], "purple"))

    # 4. Comunicação
    y_com = y_d2 + h_d2 + 64
    svg, h_com = _card(
        y_com, "llm", "4. AGENTE DE COMUNICAÇÃO", "🤖 LLM: DeepSeek V4.1 Flash",
        "no_comunicacao · Anfitrião de Brasília",
        ["• Escreve só titulo, resumo_acesso e por_que_combina (JSON Schema estrito)",
         "• Recebe os fatos de cada cartão (montar_fatos), nunca dado do cofre",
         "• Na reescrita, só os cartões reprovados mudam"],
        "Saída: fatos, cartoes")
    corpo.append(svg)
    arestas.append(_seta([(CX, y_d2 + h_d2), (CX, y_com)], "amber"))
    rotulos.append(_rotulo(CX + 14, y_d2 + h_d2 + 34, "1 ou mais validados", "amber", "start"))
    com_meio, com_fim = y_com + h_com // 2, y_com + h_com

    # 3. Validação dos textos
    y_vt = com_fim + 64
    svg, h_vt = _card(
        y_vt, "hybrid", "3. VALIDAÇÃO DOS TEXTOS", "🛡️ Código + juiz LLM",
        "no_validacao_textos · varredura dos cartões",
        ["• Varredura em código (verificar_cartoes): número, nome ou origem do cofre",
         "• Juiz, 2ª passagem (#72): contradição com os fatos e vazamento;",
         "  sem LLM, cai nas regras do próprio juiz"],
        "Saída: reprovados (só enumerações), reescritas")
    corpo.append(svg)
    arestas.append(_seta([(CX, com_fim), (CX, y_vt)], "cyan"))
    rotulos.append(_rotulo(CX + 14, com_fim + 36, "cartoes", "cyan", "start"))
    vt_meio, vt_fim = y_vt + h_vt // 2, y_vt + h_vt

    # Orquestrador: finalização
    y_fin = vt_fim + 64
    svg, h_fin = _card(
        y_fin, "code", "ORQUESTRADOR", "⚙️ Código (RNF-04)",
        "no_finalizar · monta os cartões públicos",
        ["• Preço, gasto, tempos e horário calculados por código a partir do cofre",
         "• Link do TikTok e fonte do vídeo preenchidos por código (RF-06)",
         "• Cartão ainda reprovado recebe o texto de reserva, feito por regras",
         "• Sem cartões: avisa o grupo (sem janela comum ou sem lugar viável)"],
        "Saída: resultado_final_cartoes, mensagens")
    corpo.append(svg)
    arestas.append(_seta([(CX, vt_fim), (CX, y_fin)], "amber"))
    rotulos.append(_rotulo(CX + 14, vt_fim + 36, "aprovados, ou texto de reserva", "amber", "start"))
    fin_meio, fin_fim = y_fin + h_fin // 2, y_fin + h_fin

    # fim
    y_end = fin_fim + 50
    svg, h_end = _pilula(y_end, "FIM · Tela 3: cartões para votar, ou aviso ao grupo", "#1e1b4b", "#818cf8")
    corpo.append(svg)
    arestas.append(_seta([(CX, fin_fim), (CX, y_end)], "green"))

    # cofre e canais privados
    y_cofre = y_pesq
    alto_cofre = val_fim - y_pesq
    corpo.append(_cofre(y_cofre, alto_cofre))
    meio_cofre_x = COFRE_X + COFRE_W // 2
    arestas.append(_seta([(CARD_X + CARD_W, y_pessoal + 70), (meio_cofre_x, y_pessoal + 70), (meio_cofre_x, y_cofre)],
                         "orange", tracejado=True))
    rotulos.append(_rotulo(meio_cofre_x - 14, y_pessoal + 62, "canais 1, 2 e 4", "orange", "end"))
    arestas.append(_seta([(COFRE_X, log_meio), (CARD_X + CARD_W, log_meio)], "orange", tracejado=True))
    rotulos.append(_rotulo((COFRE_X + CARD_X + CARD_W) / 2, log_meio - 10, "canal 4", "orange"))
    arestas.append(_seta([(COFRE_X, val_meio), (CARD_X + CARD_W, val_meio)], "orange", tracejado=True))
    rotulos.append(_rotulo((COFRE_X + CARD_X + CARD_W) / 2, val_meio - 10, "canais 1 e 2", "orange"))

    # laço Validação -> Pesquisa
    arestas.append(_seta([(CX - 160, d2_meio), (200, d2_meio), (200, pesq_meio), (CARD_X, pesq_meio)],
                         "amber", tracejado=True))
    rotulos.append(_rotulo(180, log_meio - 8, ["volta para a Pesquisa:", "menos de 3 validados", "e voltas < 2",
                                               "PedidoNovaBusca", "(só contagens)"], "amber"))
    # laço Validação dos textos -> Comunicação
    arestas.append(_seta([(CARD_X, vt_meio), (262, vt_meio), (262, com_meio), (CARD_X, com_meio)],
                         "purple", tracejado=True))
    rotulos.append(_rotulo(150, (com_meio + vt_meio) / 2 - 8, ["reescrita: reprovado", "e reescritas < 1",
                                                                 "(só os reprovados)"], "purple"))

    # saídas direto para o fim
    arestas.append(_seta([(CX + 130, d1_meio), (TRILHO_X, d1_meio), (TRILHO_X, fin_meio), (CARD_X + CARD_W, fin_meio)],
                         "red", tracejado=True))
    arestas.append(_seta([(CX + 160, d2_meio), (TRILHO_X, d2_meio)], "red", tracejado=True, ponta=False))
    arestas.append(f'<circle cx="{TRILHO_X}" cy="{d2_meio}" r="4" fill="{CORES_SETA["red"]}"/>')
    rotulos.append(_rotulo(800, d1_meio - 10, "não: ninguém tem horário em comum", "red", "start"))
    rotulos.append(_rotulo(CX + 176, d2_meio - 10, "nenhum validado depois de 2 voltas", "red", "start"))
    rotulos.append(_rotulo(TRILHO_X - 18, fin_meio - 12, ["direto para o fim:", "avisa o grupo, sem Comunicação"],
                           "red", "end"))

    # telemetria
    y_tel = y_end + h_end + 50
    svg, h_tel = _telemetria(y_tel)
    altura = y_tel + h_tel + 40

    fonte = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
    blocos = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LARGURA} {altura}" width="100%" height="100%" '
        f'style="background:#0f172a; font-family: {fonte};">',
        _defs(),
        "  <!-- cabeçalho e legenda -->",
        "  " + _cabecalho(),
        "  <!-- arestas -->",
        *("  " + a for a in arestas),
        "  <!-- nós -->",
        *("  " + c for c in corpo),
        "  <!-- rótulos das arestas -->",
        *("  " + r for r in rotulos),
        "  <!-- observabilidade -->",
        "  " + svg,
        "</svg>",
        "",
    ]
    return "\n".join(blocos)


def main() -> None:
    conteudo = gerar_svg_multiagente()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_bytes(conteudo.encode("utf-8"))   # \n em qualquer sistema: o arquivo é reprodutível
    print(f"SVG gerado em {SAIDA} ({len(conteudo)} bytes)")


if __name__ == "__main__":
    main()
