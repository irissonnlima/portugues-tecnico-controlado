# Como contribuir com o PTC-BR

<!-- ptc-mencoes: italico -->

O PTC-BR (Português Técnico Controlado) aceita propostas de regra, de verbete e de código. Este documento explica quem decide e como propor.

## Governança

- **Quem aprova:** o mantenedor do repositório (Irisson do Nascimento de Lima) aprova toda mudança de regra, de verbete, de glossário e de versão. Nenhuma outra pessoa ou time aprova mudança no PTC-BR geral.
- **Times:** cada time ajusta o vocabulário na própria camada (seção 7.3 da spec), sem aprovação do mantenedor. A camada vale só para o time.
- **Publicação:** só o mantenedor cria tags de versão. Toda versão tem entrada no CHANGELOG.

## Como propor

| Proposta | Caminho |
|---|---|
| Verbete novo ou mudança de verbete | Abra uma issue com o modelo "Verbete". |
| Regra nova ou mudança de regra | Abra uma issue com o modelo "Regra". |
| Falso positivo do verificador | Abra uma issue com o texto que gerou o alerta e o alerta recebido. |
| Código ou documentação | Abra um pull request. |

Toda proposta de verbete precisa de um exemplo incorreto e de um exemplo correto. O teste automático exige os dois.

## Antes de abrir um pull request

1. Rode os testes: `python3 -m unittest discover -s tests`.
2. Se mudou o vocabulário, compile: `python3 tools/compilar_vocabulario.py`.
3. Se mudou uma regra do verificador, meça o ruído em um corpus real: `python3 tools/medir_corpus.py <pasta>`.
4. Escreva a documentação segundo o próprio PTC-BR. O teste `tests/test_documentacao.py` verifica isso.

## Versões

O plugin e a especificação seguem versionamento semântico (seção 10 da spec). O mantenedor decide o número de cada versão.
