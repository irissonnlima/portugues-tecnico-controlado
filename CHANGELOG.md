# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). O plugin e a especificação têm versões separadas.

## [plugin 0.1.0 · spec 0.1.1] — 2026-10-30

### Plugin (novo)

- Estrutura de plugin do Claude Code com `plugin.json` e `marketplace.json`.
- Skill `ptc-br` com os modos revisar, reescrever e verificar, e o fluxo em cinco passos.
- `ptc_check.py`: verificador das regras PTC-03, 04, 05, 11, 12, 15, 17, 18, 21, 23 e 24, com perfis L/T/C, exceções e siglas declaradas.
- `ptc_diff.py`: checagem de preservação de números, negações, restrições, condições, alternativas, comparadores e modais.
- Rubrica do judge com perguntas binárias Q1–Q6 e saída JSON.
- 45 testes unitários, 14 pares de calibração do judge e 4 casos de `claude plugin eval`.

### Especificação 0.1.0 → 0.1.1

- **Corrigido:** o exemplo 8.2 acrescentava "três" e "competição", informações ausentes do original. O exemplo antigo virou "reescrita a evitar".
- **Corrigido:** o exemplo 8.1 trocava "fora do período de validade" por "expirado", o que reduz o escopo. O exemplo antigo virou "reescrita a evitar".
- **Novo:** tipo de verificação por regra: (A) automática, (P) parcial, (J) julgamento.
- **Novo:** matriz regra × perfil (seção 3.1). Os perfis PTC-L e PTC-C passam a ter efeito.
- **Novo:** regras de contagem de palavras e de frases (seção 5).
- **Novo:** sintaxe de exceções e de siglas conhecidas (seção 6).
- **Novo:** política de versionamento (seção 10) e roadmap revisado (seção 11).
- **Mudado:** a PTC-08 incorpora a PTC-09. A PTC-09 fica marcada como *[REMOVIDA]*, e o ID não é reutilizado.
- **Mudado:** a PTC-01 e a PTC-05 têm critérios mais objetivos; a PTC-22 proíbe acrescentar informação.
- **Mudado:** o exemplo de verbete guarda o lema, não a lista de formas flexionadas.
