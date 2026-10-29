# Plano do relatório da semana 1: definições do projeto

- **Entregável:** relatório em .docx, padrão ABNT, com **até 5 páginas de texto**. Capa e referências ficam fora da contagem.
- **Fontes:** PDF da equipe "Grupo 07 - Orquestrador de Rolês" (29/10), exportado do [documento do grupo](https://docs.google.com/document/d/1mlxgJ9XoadAl4qKV28bw6qexQxF6xpwcSx5aENsRPF4/edit?tab=t.mm6pfcuj8dpt#heading=h.tyssdhkqxqfd) (Google Docs), [requisitos v0.2](../../produto/requisitos.md), [visão do produto](../../produto/visao.md) e ADRs [0002](../../decisoes/0002-recorte-do-mvp.md) e [0003](../../decisoes/0003-canal-app-web.md).
- **Princípio de corte:** o relatório mostra as decisões e o raciocínio; o detalhe fica no repositório. Toda lista vira quadro, e cada fato aparece em uma seção só.

## 1. O que temos

| Parte | Páginas no PDF | Situação |
|---|---|---|
| Cenário, Problema, Essential Question | 2 a 4 | Pronto, mas o problema não cita nenhuma evidência |
| Guiding questions | 4 e 5 | 9 perguntas; uma delas é sobre jogos, fora do MVP |
| Personas | 6 a 13 | 7 personas com fundamentação; premissas operacionais desatualizadas (15 por sala, 18 a 40 anos) |
| Premissas | 14 a 20 | P01 a P18, quase todas sobre o projeto (equipe, prazo, custo) |
| Requisitos | 21 a 43 | 41 RF e 16 RNF no PDF; o repositório já está na v0.2, com 45 RF |
| Mapa de stakeholders | 44 a 47 | Lista em 3 níveis; inclui gamers e lojas de jogos, fora do MVP |
| Riscos | ausente | Reservar espaço |
| Métricas de sucesso | ausente | Reservar espaço |
| Repetição de capa, cenário, problema e EQ | 48 em diante | Descartar |

**Conta de espaço.** Em A4 com margens ABNT, corpo 12 e entrelinha 1,5, cabem cerca de 32 linhas (≈ 400 palavras) por página. Um quadro em fonte 10 com espaço simples cabe cerca de 55 linhas. São 5 páginas para cerca de 45 páginas de material, então a maior parte entra em quadros.

## 2. Ordem das seções e espaço de cada uma

A ordem vai do porquê ao para quem, depois ao quê e, por fim, a como saberemos se deu certo. As guiding questions ficam por último porque o quadro delas aponta para requisitos, riscos e métricas já apresentados e termina no que continua em aberto, ligando o relatório à semana 2. Se os tutores esperarem a ordem canônica do CBL, com as GQs logo depois da EQ, a seção muda de lugar sem mudar o conteúdo.

| Nº | Seção | Páginas | Formato |
|---|---|---|---|
| 1 | Cenário escolhido (com a solução proposta) | 0,45 | 2 parágrafos |
| 2 | Problema | 0,40 | 3 barreiras + evidências |
| 3 | Essential Question da equipe | 0,15 | 2 níveis + ligação com a Big Idea |
| 4 | Mapa de stakeholders | 0,35 | Quadro 1 |
| 5 | Personas | 1,00 | Quadro 2 + 1 parágrafo |
| 6 | Premissas | 0,45 | Quadro 3 |
| 7 | Requisitos funcionais e não funcionais | 1,00 | Quadros 4 e 5 |
| 8 | Riscos | 0,45 | Quadro 6 (reservado) |
| 9 | Métricas de sucesso | 0,40 | Quadro 7 (reservado) |
| 10 | Guiding questions | 0,35 | Quadro 8 |
| | **Total** | **5,00** | |
| | Referências | fora da contagem | NBR 6023 |

## 3. O que entra de cada parte

### 1 Cenário escolhido

- **Entra:** o parágrafo da equipe (hiperconectividade e distanciamento; atritos de agenda, dinheiro e decisão), reduzido a 4 linhas.
- **Acrescentar:** uma evidência de qualidade de vida, a da OMS (2025): solidão como a distância entre a conexão desejada e a real; 1 em cada 6 pessoas afetadas.
- **Acrescentar:** um parágrafo de 5 linhas sobre a **solução proposta**. Nenhuma das seções pedidas apresenta o produto, e sem isso stakeholders, personas e requisitos ficam sem chão. Conteúdo: app web em que uma IA conversa em particular com cada amigo, respeita o orçamento em sigilo, propõe 2 ou 3 planos com custo por pessoa, conduz uma decisão justa e divide os custos. Recorte: DF, adultos, salas de 2 a 20 pessoas. Fechar com os três verbos da Big Idea em uma frase.

### 2 Problema

- **Entra:** as três barreiras (comunicação e constrangimento, carga burocrática e fadiga de decisão, fricção ferramental), com 2 linhas cada.
- **Ajustar:** tirar "Steam para jogos" da fricção ferramental (jogos estão fora do MVP). Trocar por "WhatsApp para conversar, mapas para rotas e outro app para dividir a conta".
- **Acrescentar:** 2 citações, para cumprir a restrição de "evidências confiáveis". CFP Board (2026): 67% recusaram eventos por custo, e 56% não disseram que o motivo era dinheiro (pesquisa nos EUA). Liu et al. (2022): quem convida subestima o quanto o outro gosta de ser chamado.
- **Se houver tempo:** uma linha com o resultado do formulário "Pesquisa de Hábitos Sociais", com o n da amostra.

### 3 Essential Question da equipe

- **Entra:** os níveis 1 e 2, como estão.
- **Sai:** a EQ do Modo Descoberta (fora do MVP, ADR 0002).

### 4 Mapa de stakeholders

- **Formato:** Quadro 1 com as colunas Nível · Quem · Interesse ou papel · Influência (alta, média ou baixa).
- **Primários:** grupos de amigos já formados, divididos entre organizador e convidados.
- **Secundários:** estabelecimentos e organizadores de eventos do DF; fontes de dados (mapas e rotas, agenda cultural, transporte público do DF).
- **Terciários:** provedores de nuvem, LLM e voz; equipe do projeto; tutores da Residência (definem os critérios); ANPD e LGPD (regulação).
- **Sai:** "gamers casuais" e "lojas digitais (Steam, Microsoft Store, PlayStation Store)", porque jogos estão fora do MVP; e "casais", porque o público são grupos de amigos.

### 5 Personas

É a parte mais comprimida: 8 páginas viram 1.

- **Método:** 1 frase citando Cooper (1999), Courage e Baxter (2005) e Barbosa et al. (2021).
- **Quadro 2:** só as 4 personas do MVP, com as colunas Persona (nome, idade, região, papel) · Frase · Dor principal · O que exige do sistema (RF):
  - **Rafaela** (primária, organizadora): RF-03 a RF-06, RF-12, RF-24, RF-34, RF-45.
  - **Cadu** (convidado com restrições de tempo e dinheiro): RF-11, RF-18, RF-19, RF-21, RF-22, RF-43.
  - **Bia** (risco de isolamento): RF-17, RF-26 (recusa discreta), RF-44.
  - **Márcio** (inclusão digital): RF-39, RF-42, RNF-07.
- **Parágrafo "fronteiras do escopo", com 4 linhas:**
  - Patrícia (antipersona) justifica o limite de 20 pessoas por sala e a ausência de ingressos, contratos e notas fiscais.
  - Thiago (Modo Descoberta) e Lara (versão para menores, art. 14 da LGPD) ficam como expansões futuras.
- **Sai:** os três níveis de objetivos, habilidades, relacionamentos, tarefas, modelo mental, a expansão de jogos da Bia e as referências que não forem citadas no texto.
- **Ajustar:** as premissas operacionais das personas mudam para a seção 6, já corrigidas. O limite passa de 15 para 20 pessoas, o público passa a ser "adultos 18+" (as personas vão de 24 a 40 anos) e "instalam o aplicativo" vira "app web instalável, acessado pelo link de convite".

### 6 Premissas

O Quadro 3 tem as colunas ID · Premissa · Confiança · Se for falsa. São cerca de 8 linhas, juntando as premissas de produto com as de projeto. Os IDs da equipe (P01 a P18) são mantidos, e as premissas novas começam em P19.

| ID | Premissa (resumo) | Origem |
|---|---|---|
| P19 | Grupos fechados de amigos que já se conhecem; adultos 18+ no DF; salas de 2 a 20 pessoas | Personas, RF-03 |
| P01 | App web responsivo e instalável, sem app nativo nem lojas de apps | P01, ADR 0003 |
| P20 | Lugares, eventos e preços vêm de uma base curada pelo grupo (RAG), conferida por API | Requisitos §8 |
| P02 | Entregamos um protótipo funcional, não um produto para muitos usuários | P02 |
| P14 | RAG, multimodal e multiagentes são obrigatórios; a tecnologia é definida até 03/11 | P13, P14 |
| P08 | 5 pessoas com cerca de 20 h por semana cada | P08, P11 |
| P16 | Custo perto de zero: ferramentas gratuitas, até R$ 20 por membro e deploy só na semana da apresentação, com demo local de reserva | P12, P15, P16 |

- **Sai:** P03 a P07, P09, P10, P17 e P18, que tratam do tema, do calendário e do processo interno da equipe, e as colunas Responsável, Validar até e Status. Tudo isso continua no documento da equipe.

### 7 Requisitos funcionais e não funcionais

- **Abertura (2 linhas):** priorização MoSCoW, critérios de aceitação no formato QUANDO/ENTÃO e lista completa (45 RF e 16 RNF) no repositório.
- **Quadro 4:** as 12 capacidades Must da [seção 4.12 dos requisitos](../../produto/requisitos.md#412-agrupamento-para-o-documento-final), com as colunas Capacidade · RF · Persona.
- **Quadro 5:** os RNF Must agrupados em 8 linhas, com as colunas Grupo · RNF · Como verificar (meta):
  - privacidade e LGPD (RNF-01, RNF-02);
  - dados reais e cálculos fora do LLM (RNF-03, RNF-04);
  - explicabilidade (RNF-05);
  - usabilidade e acessibilidade (RNF-06 a RNF-09);
  - registro para métricas (RNF-10);
  - segurança (RNF-11);
  - arquitetura do roadmap (RNF-12);
  - justiça (RNF-13).
- **Uma frase com os Should de destaque:** caronas, Pix, foto da nota fiscal e resposta em voz.
- **Sai:** glossário, fluxo principal (resumido na solução proposta, seção 1), cenários QUANDO/ENTÃO, questões em aberto e extensões futuras (já cobertas no parágrafo de fronteiras da seção 5).

### 8 Riscos (espaço reservado)

- **Formato esperado:** Quadro 6 com as colunas ID (R-01…) · Risco · Probabilidade · Impacto · Mitigação (RF/RNF), com 6 a 8 riscos.
- **Pontos de partida:**
  - os 7 riscos da [visão](../../produto/visao.md#riscos-conhecidos);
  - a coluna Riscos dos requisitos;
  - a seção de riscos dos ADRs 0001 a 0003;
  - as premissas de confiança média (P02, P12).
- **Depois:** os IDs R-NN substituem os nomes dos riscos na coluna Riscos dos requisitos.

### 9 Métricas de sucesso (espaço reservado)

- **Formato esperado:** Quadro 7 com as colunas ID (M-01…) · Métrica · Como medir (fonte do dado) · Meta · Quando, com cerca de 6 métricas.
- **Pontos de partida:**
  - as metas provisórias dos RNF (RNF-02, RNF-03, RNF-06, RNF-13, RNF-14);
  - a "taxa de planos que viram encontros" do ADR 0001, medida pelo RF-36;
  - as hipóteses do questionário, que dão a linha de base.
- **Cuidado:** incluir ao menos uma métrica de resultado em qualidade de vida (frequência real × desejada de encontros), e não só de uso, para evitar métricas de vaidade.
- **Depois:** os IDs M-NN entram na coluna Métrica dos requisitos.

### 10 Guiding questions

O Quadro 8 tem as colunas GQ (1 linha) · Encaminhamento. Entram 8 das 9 perguntas; a de jogos baratos sai, porque jogos estão fora do MVP.

| GQ (resumo) | Encaminhamento |
|---|---|
| Imprevistos em tempo real (chuva, trem quebrado) | Em aberto: candidato a requisito de replanejamento (semanas 4 a 6) |
| Desempate e prioridade em conflito (custo × deslocamento) | RF-19 ("menor miséria", ADR pendente) e RF-25 |
| Amigo gargalo | RF-12 (prazo e ação padrão) e RF-45 |
| Espera enquanto a IA processa | RNF-14 (progresso visível, até 60 s) |
| Bolha de recomendação | Em aberto: diversidade no RF-38 |
| Restrições matematicamente excludentes | RF-13, RF-15 e RF-18 |
| Comunicar restrição sem expor o amigo | RF-11 e RNF-02 |
| Localização exata da casa | RF-01 (só região) e RNF-01 |

## 4. Ajustes de consistência antes de montar

1. Sala de **2 a 20** pessoas em todas as partes: premissas das personas e antipersona Patrícia.
2. Público: **adultos 18+**, sem o teto de 40 anos.
3. Tirar os jogos do problema e dos stakeholders. Eles aparecem só como expansão futura.
4. "Instalam o aplicativo" vira **app web instalável**, acessado pelo link de convite.
5. A antipersona diz que não há "módulos de cobrança". Ajustar para "sem faturamento, ingressos ou notas fiscais", porque o Pix entre amigos (RF-33) é só um atalho para o acerto.
6. Numeração progressiva (NBR 6024): o PDF repete "1." em várias seções.
7. Descartar a cópia repetida da capa e das primeiras seções no fim do PDF.
8. Capa: autores com nome completo (no PDF está só "Cauan") e "Brasília" com acento.

## 5. Formatação ABNT

- **Normas:** NBR 14724 (trabalhos acadêmicos), NBR 6024 (numeração), NBR 10520 (citações, sistema autor-data) e NBR 6023 (referências).
- **Página:** A4; margens de 3 cm em cima e à esquerda e de 2 cm embaixo e à direita.
- **Texto:** Times New Roman ou Arial 12, entrelinha 1,5, justificado, recuo de 1,25 cm na primeira linha.
- **Seções primárias:** em maiúsculas e negrito, numeradas (1, 2, 3…), alinhadas à esquerda.
- **Quadros:** são informação textual, então usam "Quadro", não "Tabela". Título acima ("Quadro 1 – Mapa de stakeholders"), fonte abaixo ("Fonte: elaborado pelos autores (2026)."), corpo em 10 com espaço simples. A fonte 10 dentro de quadros é prática comum; se os tutores exigirem 12, o orçamento de páginas precisa ser refeito.
- **Paginação:** algarismos arábicos no canto superior direito. A capa não é numerada.
- **Pré-textuais:** só a capa. Folha de rosto e sumário ficam de fora, porque comeriam espaço. Confirmar com os tutores se são exigidos.
- **Referências:** só as obras citadas, alinhadas à esquerda, em espaço simples, separadas por uma linha em branco. Lista provável:
  - WHO (2025);
  - CFP Board (2026);
  - Liu et al. (2022);
  - Cooper (1999);
  - Courage e Baxter (2005);
  - Barbosa et al. (2021);
  - Brasil, Lei nº 13.709/2018 (LGPD).
- **Repositório:** é privado. Se o relatório disser "lista completa no repositório", os avaliadores precisam ter acesso, ou a frase deve dizer "disponível sob solicitação".

## 6. Próximos passos

1. ~~A equipe preenche os Quadros 6 (Riscos) e 7 (Métricas) no formato acima.~~ Feito a partir dos PDFs da equipe. Riscos: entram os 6 de maior probabilidade × impacto (na numeração nova da guia Riscos: R-01, R-02, R-03, R-04, R-05, R-07); R-06, R-08 e R-09 ficam citados no texto. Métricas: entram as 3 de resultado escolhidas pelo grupo (conversão de sala em rolê, confirmação de realização e satisfação); as outras 4 ficam nas metas dos RNF.
2. A equipe valida os ajustes de consistência da seção 4 com as autoras de cada parte.
3. ~~Montar o .docx com estilos ABNT e os quadros, e conferir a contagem de páginas exportando para PDF.~~ Feito em [relatorio-semana-01.docx](relatorio-semana-01.docx): 5 páginas de texto, com cerca de 4 cm livres na última. Depois de preencher os Quadros 6 e 7, exportar para PDF e conferir se o texto continua terminando na 5ª página.
4. Depois da entrega, ligar R-NN e M-NN às colunas dos requisitos e trazer as partes da equipe (personas, premissas, stakeholders, GQs) para o repositório em Markdown, para que cada fato viva em um lugar só.

## 7. Revisão de consistência (29/10/2026)

Depois que outro agente arrumou o documento da equipe (requisitos v0.3 com o RF-46, riscos renumerados e premissas e métricas sem piloto), o relatório foi alinhado a ele. O texto continua em 5 páginas, com cerca de 1,5 cm livres na última.

- **Stakeholders:** nova linha para as integrações de compartilhamento e pagamento (WhatsApp, agendas, Pix e bancos).
- **Personas:** a Patrícia justifica a ausência de *venda* de ingressos e de *emissão* de notas fiscais, sem contradizer o RF-31. A Rafaela passa a exigir a votação como padrão e as regras de preferência da sala (RF-14). As citações entram na mesma célula do nome, para ganhar espaço.
- **Premissas:** as linhas mostram todos os IDs de origem (P13, P14; P08, P11; P12, P15, P16). A P02 troca o piloto por testes do MVP, e a P16 cita os créditos gratuitos de API. P19 e P20 continuam só no relatório até entrarem na guia Premissas.
- **Requisitos:** 46 RF (o RF-46, de imprevistos, é Could), com os 27 Must mantidos. "Decisão justa" passa a ser "Ranqueamento justo", e a frase dos Should inclui WhatsApp, agenda e rolê em casa.
- **Riscos:** IDs na numeração nova (R-04 amigo gargalo, R-05 segurança na volta, R-07 APIs; R-06, R-08 e R-09 no texto) e listas de RF/RNF atualizadas (RF-02, RF-45, RF-46, RNF-14, RNF-16).
- **Métricas:** a M-01 deixa de depender de piloto e de meta mensal e define o que é sala ativa. A M-03 indica que o RF-37 é Should e que a média sai com a taxa de resposta. A coluna "Quando" foi juntada à meta.
- **Guiding questions:** a GQ 1 aponta para o RF-46, e a GQ 2 cita a regra de datas do organizador (RF-14). A GQ 8 (localização da casa) saiu, como na guia.
