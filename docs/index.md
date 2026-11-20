# Orquestrador de Rolês

> **Assistente Inteligente para Encontros no Distrito Federal**  
> *Grupo 7 • Residência em Inteligência Artificial (Instituto Eldorado & Universidade de Brasília)*

O **Orquestrador de Rolês** é um sistema que ajuda grupos de amigos a decidirem onde se encontrar em Brasília e nas Regiões Administrativas do DF, de forma justa e sem complicação.

---

### O que o sistema resolve?

* 🤐 **Ninguém passa vergonha com dinheiro:** cada amigo informa em segredo o seu teto de gastos. O sistema calcula tudo no servidor e ninguém no grupo descobre quem tem orçamento mais apertado.
* 🚌 **Ninguém fica com o trajeto mais puxado:** nosso cálculo logístico prioriza locais equilibrados para quem mora mais longe (regra da *Menor Miséria*), evitando encontros inacessíveis para quem depende de ônibus ou metrô.
* 📍 **Lugares de verdade, sem alucinação:** o sistema pesquisa apenas em uma base curada com 93 locais reais do DF comprovados por vídeos do TikTok.

---

### Acessos Rápidos

=== "🤖 Grafo de Agentes"
    Descubra como os 5 agentes autônomos (Pessoal, Pesquisa, Logística, Validação e Comunicação) trabalham juntos no LangGraph para montar os cartões de sugestão.  
    👉 [Ver Arquitetura e Diagrama do Grafo](arquitetura/multiagente.md)

=== "📅 Entregas Semanais"
    Acompanhe a evolução do projeto semana a semana, desde as primeiras pesquisas até o protótipo multiagente funcional.  
    👉 [Ir para a Semana 04 (Multiagente)](semanas/semana-04.md)

=== "📊 Observabilidade (Langfuse)"
    Todas as chamadas de modelos, tokens gastos, custos em dólar e latência são monitorados em tempo real no Langfuse Cloud.  
    👉 [Acessar Painel do Langfuse Cloud ↗](https://cloud.langfuse.com)

---

### Equipe (Grupo 7)

| Integrante | O que faz no projeto | GitHub |
| :--- | :--- | :--- |
| **Cauan Soares** | Arquitetura de Agentes e LangGraph | [@cadasiso](https://github.com/cadasiso) |
| **Letícia Miti Takahashi** | Curadoria da Base e RAG | [@mitii05](https://github.com/mitii05) |
| **Maria Carolina** | Telas, Identidade Visual e Diagramas | [@mcznh](https://github.com/mcznh) |
| **Maria Eduarda (Duda)** | Infraestrutura, DevOps e Telemetria | [@eduarda-ogomes](https://github.com/eduarda-ogomes) |
| **Samara Letícia** | Logística, Trajetos e Mobilidade no DF | [@samarawwleticia](https://github.com/samarawwleticia) |

---

### Histórico de Versões

| Versão | Data | O que mudou? | Autor(a) |
| :---: | :---: | :--- | :--- |
| `1.0` | 10/11/2026 | Estrutura inicial da documentação e padrões do projeto. | [@eduarda-ogomes](https://github.com/eduarda-ogomes) |
| `1.1` | 17/11/2026 | Inclusão do diagrama de arquitetura dos agentes. | [@mcznh](https://github.com/mcznh) |
| `2.0` | 20/11/2026 | Visual noturno limpo, abas superiores e catálogo das semanas 1 a 4. | [@eduarda-ogomes](https://github.com/eduarda-ogomes) |
