# Semana 5 — Agentes multimodais

**Entregável:** assistente de IA multimodal, com pelo menos duas modalidades, documentação (modalidades, limitações, casos de falha e mitigação) e demonstração com evidência de uso.

**Escolha:** texto e áudio. A voz volta só no campo de horários da Tela 2 ([ADR 0017](../decisoes/0017-voz-no-campo-de-horarios.md), proposta). A foto da nota fiscal, prevista no guia, fica para depois. O trabalho é do Cauan; as demais integrantes cuidam do design e da usabilidade.

**Entrega:** [ASSISTENTE_MULTIMODAL.md](../entregas/semana-05/ASSISTENTE_MULTIMODAL.md) e [log da demonstração](../entregas/semana-05/DEMO_MULTIMODAL_LOG.txt).

## 24/11 (Cauan)

- **Diagnóstico:** nenhum conteúdo enviado pelo usuário era processado além de texto. A transcrição de 05/11 (ADR 0006) ainda existia numa branch local e funciona.
- **Interpretador do campo 2:** era o gargalo, com erros silenciosos. Texto do gabarito de 16 para 17 de 17; transcrições reais de 05/11, de 4 para 6 de 6 ([experimento](../experimentos/2026-11-24-horarios-fala.md)). Hora não usada vira pergunta. A lista do resumo passou a dizer quando a pessoa **não** pode.
- **Voz:** `src/voz/` (OpenRouter com ZDR, Groq e DeepInfra de reserva), rota com consentimento, limites e cotas; componente `voz.js` na Tela 2.
- **Medição:** 46 de 46 com voz sintética; o vocabulário com horas fazia o modelo ouvir "19h" em "nove" e foi trocado ([experimento](../experimentos/2026-11-24-voz-horarios.md)).
- **Demonstração:** `make demo-multimodal`. Trocar só a fala de uma pessoa muda a janela do grupo.
- **Para julgar mais áudios:** [eval/voz/README.md](../../eval/voz/README.md). Só arquivo e gabarito, sem mexer no código.

### Pendências

- Acordo do grupo sobre o ADR 0017; depois, atualizar o `GUIA_OFICIAL_PROJETO.md` (ainda diz "sem voz") e a situação do ADR 0009.
- Gravações: conjunto cego e mais pessoas, com o termo novo; confirmação de quem gravou em 05/11.
- Teste com microfone real no Android e no iPhone.
- Chave da OpenRouter no servidor publicado: sem ela, o botão não aparece.
- RNF-14: os agentes passaram de 60 s em uma rodada (64,9 s). O juiz dos cartões precisa de limite de tempo com reserva por regras.
- A lista do resumo da Tela 2 mostra o código da macrorregião ("oeste_proximo") em "Saindo de" (`perfil.js`), para quem cuida da tela.
