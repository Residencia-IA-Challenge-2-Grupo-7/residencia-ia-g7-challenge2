# 0002 — Recorte do MVP: só o modo com amigos

- **Status:** aceita
- **Data:** 2026-10-29
- **Semana do roadmap:** 1

## Contexto

A [visão do produto](../produto/visao.md) inclui três frentes: o modo com amigos, o Modo Descoberta (grupos novos entre desconhecidos) e o plano B com videogames. O grupo também cogitou uma versão para menores de idade, em que os responsáveis participam da escolha dos planos (sem bares, sem rolês tarde da noite). O [ADR 0001](0001-escolha-do-orquestrador-de-roles.md) já apontava que o escopo completo não cabe em 7 semanas.

## Opções consideradas

1. **Tudo no MVP.** Maior diferencial, mas inviável no prazo. O Modo Descoberta sozinho exige verificação de identidade, moderação e regras de segurança entre desconhecidos.
2. **Só o modo com amigos.** Concentra o núcleo do problema (encontros que morrem na organização) e os diferenciais (IA intermediária, orçamento em sigilo, plano completo com custo por pessoa, decisão justa), com menos riscos de segurança.
3. **Modo com amigos e videogames.** A Steam só expõe perfis públicos, Xbox e PlayStation não têm API aberta, e o plano B desvia o foco do encontro presencial.

## Decisão

O MVP cobre só o **modo com amigos**. O Modo Descoberta, os videogames e plano B online e a versão para menores de idade ficam como extensões futuras.

## Justificativa e evidências

- O modo com amigos responde à Essential Question de nível 2 e ataca a solidão de quem tem rede, mas quase não a encontra (definição da OMS, na visão).
- O produto prioriza o presencial: contato presencial frequente está associado a menos depressão, e contato à distância não mostra efeito consistente (Teo et al., 2015, na visão).
- A versão para menores exige tratar dados de crianças e adolescentes no seu melhor interesse (art. 14 da LGPD) e fluxos de aprovação pelos responsáveis, o que mudaria o produto inteiro.
- Decisão tomada em grupo; requisitos do recorte em [docs/produto/requisitos.md](../produto/requisitos.md).

## Riscos e limitações

- Quem não tem amigos para chamar não é atendido no MVP. A Essential Question do Modo Descoberta fica sem resposta neste ciclo.
- O público passa a ser só de adultos (18+).

## Como vamos validar

- Se o formulário mostrar que a demanda por novas conexões (hipótese H7) supera com folga a dor de coordenação (H2), revisitar esta decisão.
- No piloto da semana 7, medir os encontros realizados entre grupos de amigos já existentes.
