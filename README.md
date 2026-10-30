# PTC-BR — Português Técnico Controlado

Plugin do Claude Code para revisar, reescrever e verificar textos técnicos em português brasileiro com regras de linguagem controlada. A especificação se inspira no ASD-STE100 e na linguagem simples (ABNT NBR ISO 24495-1), mas é uma proposta independente e experimental.

| Componente | Versão |
|---|---|
| Plugin (`.claude-plugin/plugin.json`) | 0.2.0 |
| Especificação (`skills/ptc-br/references/regras.md`) | 0.2.0 |

## O que o plugin faz

- **Revisar:** aponta violações com o ID da regra (PTC-NN), o nível e uma sugestão. Classifica o texto como *Conforme*, *Conforme com exceções* ou *Não conforme*.
- **Reescrever:** reescreve só as frases com achado (diff mínimo). Cada par original → reescrita passa pelo judge.
- **Verificar:** diz se uma reescrita preserva o sentido do original.

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
    vocabulario/         verbetes em YAML (fonte editável) e schema.json
  scripts/
    ptc_check.py         verificador das regras automáticas e parciais
    ptc_diff.py          checagem determinística de preservação de sentido (PTC-22)
    lexico.json          listas: palavras vagas, deverbais, siglas conhecidas, unidades…
    vocabulario.json     vocabulário compilado (gerado; não edite à mão)
tools/
  compilar_vocabulario.py  valida os YAML e gera vocabulario.json (requer PyYAML)
  medir_corpus.py          mede achados por regra em um corpus, para controlar falsos positivos
tests/                   testes unitários dos scripts
tests/judge/             pares rotulados e calibração do judge
evals/                   casos do `claude plugin eval` (comportamento da skill)
```

## Scripts (só biblioteca padrão do Python 3.10+)

```bash
python3 skills/ptc-br/scripts/ptc_check.py docs/manual.md --perfil T
python3 skills/ptc-br/scripts/ptc_check.py --texto "Realize a verificação do log." --json
python3 skills/ptc-br/scripts/ptc_check.py docs/manual.md --siglas siglas-do-time.txt   # siglas conhecidas do público
python3 skills/ptc-br/scripts/ptc_diff.py --original "Só admins acessam." --reescrita "Admins acessam."
```

Código de saída: `0` sem problema grave, `1` com violação obrigatória de alta confiança (check) ou alerta alto (diff), `2` erro.

## Editar o vocabulário

1. Edite ou acrescente verbetes em `skills/ptc-br/references/vocabulario/*.yaml`. Use um ID novo; nunca reutilize um ID.
2. Compile e valide: `python3 tools/compilar_vocabulario.py`.
3. Rode os testes. O teste `ExemplosDosVerbetes` exige que o `exemplo_incorreto` dispare o alerta e o `exemplo_correto` não.
4. Meça o ruído em um corpus real: `python3 tools/medir_corpus.py <pasta>`.

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

Ainda não definida. Sugestão em discussão: CC BY 4.0 para a especificação e MIT para o código.
