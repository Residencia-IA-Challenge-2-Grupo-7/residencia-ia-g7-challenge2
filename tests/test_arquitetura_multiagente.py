"""
Testes unitários e de integridade para a documentação e diagramas da arquitetura multiagente.
Issue #75: [Semana 4] [DOCS] Diagrama Visual da Arquitetura do Grafo Multiagente (Mermaid & SVG)
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import yaml
from scripts.gerar_grafo_multiagente_svg import gerar_svg_multiagente


def test_gerador_svg_retorna_svg_valido():
    svg_str = gerar_svg_multiagente()
    assert isinstance(svg_str, str)
    assert "<svg" in svg_str
    assert "</svg>" in svg_str

    # Validação do XML do SVG gerado
    root = ET.fromstring(svg_str)
    assert root.tag.endswith("svg")
    assert "viewBox" in root.attrib


def test_arquivo_svg_grafo_multiagente_existe_e_e_valido():
    svg_path = Path("docs/arquitetura/img/grafo_multiagente.svg")
    assert svg_path.exists(), f"Arquivo SVG não encontrado em {svg_path}"

    content = svg_path.read_text(encoding="utf-8")
    assert len(content) > 5000, "Arquivo SVG está vazio ou truncado"
    assert content == gerar_svg_multiagente(), "O arquivo SVG precisa estar sincronizado com o gerador"

    # Parse XML
    root = ET.fromstring(content)
    assert root.tag.endswith("svg")


def test_svg_contem_todos_os_nos_canais_e_requisitos_do_grafo():
    svg_path = Path("docs/arquitetura/img/grafo_multiagente.svg")
    content = svg_path.read_text(encoding="utf-8")

    # Nós reais do grafo compilado (src/agentes/grafo.py)
    assert "0. AGENTE PESSOAL" in content
    assert "no_pessoal" in content
    assert "no_consolidar_grupo" in content
    assert "1. AGENTE DE PESQUISA" in content
    assert "no_pesquisa" in content
    assert "2. AGENTE DE LOGÍSTICA" in content
    assert "no_logistica" in content
    assert "3. AGENTE DE VALIDAÇÃO" in content
    assert "no_validacao" in content
    assert "4. AGENTE DE COMUNICAÇÃO" in content
    assert "no_comunicacao" in content
    assert "3. VALIDAÇÃO DOS TEXTOS" in content
    assert "no_validacao_textos" in content
    assert "no_finalizar" in content

    # Cofre do servidor e 4 canais na ordem real de pessoal.py (RNF-02)
    assert "COFRE DO SERVIDOR" in content
    assert "Canal 1 · orçamento" in content
    assert "Canal 2 · restrições" in content
    assert "canal 3 · preferências (o único público)" in content
    assert "Canal 4 · logística" in content

    # Laços, saídas diretas e observabilidade
    assert "avaliar_convergencia" in content
    assert "PedidoNovaBusca" in content
    assert "reescritas" in content
    assert "direto para o fim" in content
    assert "RNF-02" in content
    assert "RNF-04" in content
    assert "RNF-14" in content
    assert "60 s" in content
    assert "Langfuse" in content


def test_documento_multiagente_md_existe_e_reflete_grafo_implementado():
    md_path = Path("docs/arquitetura/multiagente.md")
    assert md_path.exists(), f"Arquivo não encontrado: {md_path}"

    text = md_path.read_text(encoding="utf-8")

    # Deve conter diagrama Mermaid e referência ao SVG
    assert "```mermaid" in text
    assert "flowchart TD" in text
    assert "img/grafo_multiagente.svg" in text

    # Nós reais do grafo e especificação dos 5 agentes
    for termo in (
        "Agente 0",
        "Agente 1",
        "Agente 2",
        "Agente 3",
        "Agente 4",
        "no_pessoal",
        "no_consolidar_grupo",
        "no_pesquisa",
        "no_logistica",
        "no_validacao",
        "no_comunicacao",
        "no_validacao_textos",
        "no_finalizar",
    ):
        assert termo in text, f"Termo ausente em multiagente.md: {termo}"

    # Contrato real de MultiAgentState (src/agentes/estado.py) e Cofre fora do estado
    assert "MultiAgentState" in text
    assert "Cofre" in text
    assert "serializar_estado" in text
    assert "membros_privados" not in text, "Dados privados ficam no Cofre, nunca em MultiAgentState"
    for campo_real in (
        "membros_anonimos",
        "preferencias_grupo",
        "candidatos_pesquisa",
        "candidatos_avaliados",
        "relatorio_validacao",
        "candidatos_validados",
        "cartoes",
        "reprovados",
        "resultado_final_cartoes",
        "mensagens",
        "historico_erros",
    ):
        assert campo_real in text, f"Campo de estado.py ausente: {campo_real}"

    # Spans reais do Langfuse e RNF-14 (60 s para gerar planos)
    for span in (
        "agente_pessoal",
        "consolidar_grupo",
        "pesquisa",
        "logistica",
        "validacao",
        "comunicacao",
        "validacao_textos",
        "finalizar",
    ):
        assert span in text, f"Span do Langfuse ausente: {span}"
    assert "60" in text
    assert "Menor Miséria" in text
    assert "RNF-02" in text
    assert "RNF-03" in text
    assert "RNF-04" in text


def test_mkdocs_contem_referencia_multiagente():
    mkdocs_path = Path("mkdocs.yml")
    assert mkdocs_path.exists()

    class MkDocsLoader(yaml.SafeLoader):
        pass

    MkDocsLoader.add_multi_constructor(
        "tag:yaml.org,2002:python/name:",
        lambda loader, suffix, node: suffix,
    )

    data = yaml.load(mkdocs_path.read_text(encoding="utf-8"), Loader=MkDocsLoader)

    nav = data.get("nav", [])
    nav_str = str(nav)
    assert "arquitetura/multiagente.md" in nav_str

    exts = data.get("markdown_extensions", [])
    superfences_found = False
    for ext in exts:
        if isinstance(ext, dict) and "pymdownx.superfences" in ext:
            custom_fences = ext["pymdownx.superfences"].get("custom_fences", [])
            for cf in custom_fences:
                if cf.get("name") == "mermaid":
                    superfences_found = True
    assert superfences_found, "custom_fences com mermaid não encontrada em pymdownx.superfences"


def test_documento_multiagente_html_existe_e_e_valido():
    html_path = Path("docs/arquitetura/multiagente.html")
    assert html_path.exists(), f"Arquivo não encontrado: {html_path}"

    html = html_path.read_text(encoding="utf-8")
    assert len(html) > 5000, "Arquivo HTML está vazio ou incompleto"

    assert "<!doctype html>" in html.lower()
    assert "<html" in html.lower()
    assert "<body" in html.lower()
    assert "</html>" in html.lower()

    assert "img/grafo_multiagente.svg" in html
    assert "mermaid" in html.lower()

    # Presença dos 5 agentes e dos nós do grafo
    assert "0. Agente Pessoal" in html
    assert "1. Agente de Pesquisa" in html
    assert "2. Agente de Logística" in html
    assert "3. Agente de Validação" in html
    assert "4. Agente de Comunicação" in html
    assert "no_consolidar_grupo" in html
    assert "no_validacao_textos" in html
    assert "no_finalizar" in html

    # Canais na ordem real de pessoal.py (Canal 3 = Preferências públicas, Canal 4 = Logística no Cofre)
    assert "Canal 1: Orçamento Sigiloso" in html
    assert "Canal 2: Restrições Duras" in html
    assert "Canal 3: Preferências" in html
    assert "Canal 4: Logística" in html
    assert "membros_privados" not in html
    assert "membros_anonimos" in html
    assert "resultado_final_cartoes" in html
    assert "RNF-02" in html
    assert "RNF-03" in html
    assert "RNF-04" in html
    assert "60 s" in html
    assert "Langfuse" in html
    assert "Menor Miséria" in html

    # index.html é publicado sozinho por publicar.sh (docs/arquitetura/AGENTS.md) e não deve ter link quebrado
    index_path = Path("docs/arquitetura/index.html")
    assert index_path.exists()
    assert "multiagente.html" not in index_path.read_text(encoding="utf-8")
