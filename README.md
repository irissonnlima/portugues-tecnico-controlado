# PTC-BR — Português Técnico Controlado

<!-- ptc-mencoes: italico -->

Plugin do Claude Code para revisar, reescrever e verificar textos técnicos em português brasileiro com regras de linguagem controlada. A especificação se inspira no ASD-STE100 (Simplified Technical English) e na linguagem simples (ABNT NBR ISO 24495-1), mas é uma proposta independente e experimental.

| Componente | Versão |
|---|---|
| Plugin (`.claude-plugin/plugin.json`) | 0.6.1 |
| Especificação (`skills/ptc-br/references/regras.md`) | 0.6.0 |

## O que o plugin faz

- **Revisar:** aponta violações com o ID da regra (PTC-NN), o nível e uma sugestão. Classifica o texto como *Conforme*, *Conforme com exceções* ou *Não conforme*.
- **Reescrever:** reescreve só as frases com achado (diff mínimo). Cada par original → reescrita passa pelo judge.
- **Verificar:** diz se uma reescrita preserva o sentido do original.

## Probabilidade com percentual (PTC-26)

Termos de certeza seguem uma escala fixa, baseada na Intelligence Community Directive 203 (ICD 203), padrão da comunidade de inteligência dos EUA. A ICD 203 atualiza a tabela de Sherman Kent (CIA, 1964). Toda ocorrência traz a faixa entre parênteses: *A causa provável (55–80%) é o certificado.*

| Termo | Faixa | Termo | Faixa |
|---|---|---|---|
| quase impossível | 1–5% | provável | 55–80% |
| muito improvável | 5–20% | muito provável | 80–95% |
| improvável | 20–45% | quase certo | 95–99% |
| chance equilibrada | 45–55% | | |

O verificador aponta o termo sem percentual e o número fora da faixa (*muito provável (60%)*). Expressões vagas (*talvez*, *possivelmente*) devem virar um termo da escala, e a escolha do nível é do autor.

## Instalação

```bash
claude plugin marketplace add /caminho/para/portugues-tecnico-controlado   # ou <owner>/<repo> no GitHub
claude plugin install ptc-br@ptc-br
```

Uso: peça "revise este texto em PTC" ou chame `/ptc-br:ptc-br revisar docs/manual.md`.

## Estrutura

```
.claude-plugin/          plugin.json e marketplace.json
skills/ptc-br/
  SKILL.md               fluxo da skill: script → passada global → passada local → reescrita → judge
  references/
    regras.md            especificação PTC-BR (regras, perfis, contagem, exceções)
    rubrica-judge.md     perguntas binárias Q1–Q6 e formato JSON do judge
    vocabulario/         verbetes em YAML (geral, formal, polissemia, probabilidade, anglicismos) e schema.json
    glossarios/          glossários de domínio: software, dados, infraestrutura, finanças
  scripts/
    ptc_check.py         verificador das regras automáticas e parciais
    ptc_diff.py          checagem determinística de preservação de sentido (PTC-22)
    ptc_vocab.py         flexão, regex e camadas de vocabulário
    lexico.json          listas: palavras vagas, deverbais, siglas conhecidas, unidades…
    vocabulario.json     vocabulário compilado (gerado; não edite à mão)
tools/
  compilar_vocabulario.py  valida os YAML e gera vocabulario.json (requer PyYAML)
  medir_corpus.py          mede achados por regra em um corpus, para controlar falsos positivos
exemplos/
  camada-time.yaml       modelo de camada de vocabulário de um time
tests/                   testes unitários dos scripts
tests/judge/             pares rotulados e calibração do judge
evals/                   casos do `claude plugin eval` (comportamento da skill)
.github/workflows/       CI: testes com e sem dependências opcionais
```

## Scripts (só biblioteca padrão do Python 3.10+)

```bash
python3 skills/ptc-br/scripts/ptc_check.py docs/manual.md --perfil T
python3 skills/ptc-br/scripts/ptc_check.py --texto "Realize a verificação do log." --json
python3 skills/ptc-br/scripts/ptc_check.py docs/manual.md --siglas siglas-do-time.txt   # siglas conhecidas do público
python3 skills/ptc-br/scripts/ptc_check.py docs/manual.md --vocabulario exemplos/camada-time.yaml
python3 skills/ptc-br/scripts/ptc_check.py docs/manual.md --lematizar   # opcional: pip install simplemma
python3 skills/ptc-br/scripts/ptc_check.py docs/manual.md --dominios software,dados
python3 skills/ptc-br/scripts/ptc_diff.py --original "Só admins acessam." --reescrita "Admins acessam."
```

Código de saída: `0` sem problema grave, `1` com violação obrigatória de alta confiança (check) ou alerta alto (diff), `2` erro.

## Usar no CI (GitHub Action)

A Action anota os achados nas linhas do pull request e escreve um resumo na página da execução:

```yaml
- uses: actions/checkout@v5
  with:
    fetch-depth: 0            # para comparar com a base do PR
- uses: irissonnlima/portugues-tecnico-controlado@v0.6.1
  with:
    ignorar: "evals/** CHANGELOG.md"        # opcional
    vocabulario: docs/camada-do-time.json   # opcional
    min-confianca: media                    # padrão
    falhar-em: obrigatoria-alta             # padrão; também: obrigatoria, qualquer, nunca
```

Sem `arquivos`, a Action verifica os `.md` alterados no push ou no PR.

## Usar no pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/irissonnlima/portugues-tecnico-controlado
    rev: v0.6.1
    hooks:
      - id: ptc-br
        args: [--min-confianca, media, --falhar-em, obrigatoria-alta, --vocabulario, docs/camada-do-time.json]
```

O hook roda `tools/ptc_lote.py`, que também funciona sozinho: `python3 tools/ptc_lote.py docs/*.md`.

## Registro de aceitação

A skill registra o que a pessoa fez com cada achado: aceito, descartado ou exceção. O registro fica só na máquina da pessoa (`~/.local/share/ptc-br/aceitacao.jsonl`) e não guarda o texto. O resumo mostra a taxa de aceitação por regra e aponta as regras a revisar:

```bash
python3 skills/ptc-br/scripts/ptc_registro.py resumo --excecoes docs/
```

Um time pode juntar os registros de várias pessoas com `--registro a.jsonl --registro b.jsonl`.

## Marcações no próprio documento

Comentários HTML ajustam a verificação sem mudar o texto renderizado (seção 6 da spec):

- `<!-- ptc-ignorar: motivo -->`: o próximo bloco fica fora (ex.: um exemplo incorreto de propósito).
- `<!-- ptc-idioma: en -->`: o próximo bloco está em inglês. Blocos em inglês também são detectados automaticamente e seguem o perfil ASD-STE100 (Simplified Technical English): frases curtas, voz ativa, imperativo nos passos. A checagem de gênero e as demais regras próprias do português não valem para eles.
- `<!-- ptc-mencoes: italico -->`: termos em itálico são citações (*utilizar*), não uso.
- `<!-- ptc-excecao: PTC-03; motivo: ... -->` e `<!-- ptc-siglas: API, SQL -->`.

## Camada de vocabulário do time

O PTC-BR geral fica neutro em escolhas que variam por time. Por exemplo, aceita *verificar* e *conferir* como sinônimos. Cada time registra as próprias escolhas em uma camada (YAML ou JSON). A camada muda verbetes (`sobrepor`), acrescenta verbetes (`verbetes`) e declara siglas (`siglas`). Ela também aceita substantivos técnicos em *-ing* nos blocos em inglês (`ingles.ing_aceitos`). Veja `exemplos/camada-time.yaml` e a seção 7.3 da spec.

## Editar o vocabulário

1. Edite ou acrescente verbetes em `skills/ptc-br/references/vocabulario/*.yaml`. Use um ID novo; nunca reutilize um ID.
2. Compile e valide: `python3 tools/compilar_vocabulario.py`.
3. Rode os testes. O teste `ExemplosDosVerbetes` exige que o `exemplo_incorreto` dispare o alerta e o `exemplo_correto` não.
4. Meça o ruído em um corpus real: `python3 tools/medir_corpus.py <pasta>`.

## O projeto segue as próprias regras

A documentação deste repositório (README, CHANGELOG, SKILL.md, spec e rubrica) passa no verificador. O teste `tests/test_documentacao.py` falha se um desses arquivos tiver achado de confiança média ou alta. A CI do GitHub roda esse teste em todo push.

## Testes em três camadas

| Camada | O que mede | Comando | Custo |
|---|---|---|---|
| Unitários | Contagem, regras e diff | `python3 -m unittest discover -s tests` | zero |
| Calibração do judge | Concordância do judge com rótulos humanos | `python3 tests/judge/calibrar.py --runs 3` | 1 chamada por caso e execução |
| Evals da skill | Comportamento de ponta a ponta | `claude plugin eval . --allow-tools Bash --runs 3` | maior |

Rode os unitários a cada mudança. Rode a calibração quando mudar a rubrica ou os casos. Rode os evals antes de publicar uma versão.

## Versionamento

- O **plugin** e a **especificação** têm versões separadas (seção 10 de `regras.md`).
- Toda mudança entra no `CHANGELOG.md`.
- Publique com tag git: `v0.1.0` para o plugin; a versão da spec fica no cabeçalho de `regras.md`.

## Licença

[MIT](LICENSE). Vale para o código, a especificação e o vocabulário.

## Governança

Só o mantenedor do repositório aprova mudança de regra, de verbete e de versão. Para propor, veja o [CONTRIBUTING.md](CONTRIBUTING.md).
