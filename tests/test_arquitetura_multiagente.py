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
    
    # Parse XML
    root = ET.fromstring(content)
    assert root.tag.endswith("svg")

def test_svg_contem_todos_os_agentes_e_requisitos_chave():
    svg_path = Path("docs/arquitetura/img/grafo_multiagente.svg")
    content = svg_path.read_text(encoding="utf-8")

    # Nós dos 5 agentes
    assert "0. AGENTE PESSOAL" in content
    assert "1. AGENTE DE PESQUISA" in content
    assert "2. AGENTE DE LOGÍSTICA" in content
    assert "3. AGENTE DE VALIDAÇÃO" in content
    assert "4. AGENTE DE COMUNICAÇÃO" in content

    # 4 Canais de dados (RNF-02)
    assert "Canal 1 (Orçamento)" in content
    assert "Canal 2 (Restrições)" in content
    assert "Canal 3 (Origens &amp; Horas)" in content or "Canal 3 (Origens & Horas)" in content
    assert "Canal 4 (Vibes do Grupo)" in content

    # Ciclo condicional e decisão de parada
    assert "Avaliador de" in content and "Convergência" in content
    assert "CICLO CONDICIONAL" in content
    assert "Aprovados" in content

    # Requisitos não funcionais e ADRs
    assert "RNF-02" in content  # Sigilo
    assert "RNF-04" in content  # Cálculos fora do LLM
    assert "Langfuse" in content or "LANGFUSE" in content  # Observabilidade

def test_documento_multiagente_md_existe_e_esta_completo():
    md_path = Path("docs/arquitetura/multiagente.md")
    assert md_path.exists(), f"Arquivo não encontrado: {md_path}"
    
    text = md_path.read_text(encoding="utf-8")

    # Deve conter diagrama Mermaid
    assert "```mermaid" in text
    assert "flowchart TD" in text

    # Deve referenciar a imagem SVG
    assert "img/grafo_multiagente.svg" in text

    # Deve cobrir a especificação dos 5 agentes
    assert "Agente 0" in text
    assert "Agente 1" in text
    assert "Agente 2" in text
    assert "Agente 3" in text
    assert "Agente 4" in text

    # Deve conter contrato de estado MultiAgentState
    assert "MultiAgentState" in text
    assert "membros_privados" in text
    assert "perfil_grupo_anonimizado" in text
    assert "candidatos_pesquisa" in text
    assert "candidatos_avaliados" in text
    assert "candidatos_validados" in text
    assert "resultado_cartoes" in text

    # Telemetria e requisitos
    assert "Langfuse" in text
    assert "Menor Miséria" in text
    assert "RNF-02" in text
    assert "RNF-03" in text
    assert "RNF-04" in text

def test_mkdocs_contem_referencia_multiagente():
    mkdocs_path = Path("mkdocs.yml")
    assert mkdocs_path.exists()
    
    # Custom constructor para tags python/name do PyYAML no MkDocs
    class MkDocsLoader(yaml.SafeLoader):
        pass

    MkDocsLoader.add_multi_constructor(
        "tag:yaml.org,2002:python/name:",
        lambda loader, suffix, node: suffix
    )

    data = yaml.load(mkdocs_path.read_text(encoding="utf-8"), Loader=MkDocsLoader)
    
    # Navegação
    nav = data.get("nav", [])
    nav_str = str(nav)
    assert "arquitetura/multiagente.md" in nav_str
    
    # Extensão superfences e mermaid
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
    
    # Estrutura HTML básica
    assert "<!doctype html>" in html.lower()
    assert "<html" in html.lower()
    assert "<body" in html.lower()
    assert "</html>" in html.lower()

    # Referência à imagem SVG e Mermaid
    assert "img/grafo_multiagente.svg" in html
    assert "mermaid" in html.lower()

    # Presença dos 5 agentes
    assert "0. Agente Pessoal" in html
    assert "1. Agente de Pesquisa" in html
    assert "2. Agente de Logística" in html
    assert "3. Agente de Validação" in html
    assert "4. Agente de Comunicação" in html

    # Canais de dados e requisitos
    assert "Canal 1: Orçamento Sigiloso" in html
    assert "Canal 2: Restrições Duras" in html
    assert "Canal 3: Origens e Janelas" in html
    assert "Canal 4: Vibes Coletivas" in html
    assert "RNF-02" in html
    assert "RNF-03" in html
    assert "RNF-04" in html
    assert "Langfuse" in html
    assert "Menor Miséria" in html

    # Mapa principal aponta para multiagente.html
    index_path = Path("docs/arquitetura/index.html")
    assert index_path.exists()
    assert "multiagente.html" in index_path.read_text(encoding="utf-8")

