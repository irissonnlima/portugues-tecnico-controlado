# Changelog

<!-- ptc-mencoes: italico, aspas -->

Histórico de versões do PTC-BR (Português Técnico Controlado). O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). O plugin e a especificação têm versões separadas.

## [plugin 0.5.0 · spec 0.5.0] — 2026-11-01

### Blocos em inglês: perfil ASD-STE100 (novo)

- Blocos em inglês, marcados com `ptc-idioma: en` ou detectados, deixam de ser ignorados. Eles seguem o núcleo do ASD-STE100 (seção 6.2 da spec):
  - limites de 20 palavras por instrução, 25 por descrição e 6 frases por parágrafo;
  - voz ativa, imperativo nos passos e aviso com consequência;
  - amostra de substituições de vocabulário (*utilize* → *use*) e forma *-ing* com confiança baixa.
- As regras próprias do português não valem nesses blocos: gênero do glossário, vocabulário em português, escala de probabilidade e negações.
- `--ingles ignorar` volta ao comportamento anterior. Outro idioma marcado (`es`, `fr`) continua fora da verificação.
- Um bloco sem palavra funcional (*No issues found*) segue o idioma da maioria do documento. Isso resolve o alerta de gênero em frase curta em inglês.
- No corpus de skills de um time (60 arquivos), 122 blocos em inglês passaram a ser verificados, com 15 achados, a maioria de confiança baixa.

### Outros

- CI: `actions/checkout@v5` e `actions/setup-python@v6` (as versões anteriores usavam Node 20, descontinuado).
- 129 testes unitários.

## [plugin 0.4.0 · spec 0.4.0] — 2026-11-01

### Probabilidade com percentual (novo)

- Regra **PTC-26**: termos de certeza seguem uma escala de 7 níveis, baseada na Intelligence Community Directive 203 (ICD 203). Toda ocorrência traz a faixa entre parênteses: "provável (55–80%)".
- O verificador aponta o termo sem percentual e o número fora da faixa, e sugere o termo certo para o número.
- Expressões vagas (*talvez*, *possivelmente*, *é possível que*, *certamente*) viram alerta. "É possível exportar" (capacidade) não é marcado.
- `ptc_diff.py` compara o grau de certeza. Trocar *provável* por *quase certo* é alerta alto. Escolher um nível para um *talvez* pede confirmação do autor.

### Anglicismos e glossários (novo)

- Política: substantivos técnicos em inglês aprovados, sem itálico e com gênero; verbos aportuguesados não preferidos (*commitar*, *deployar*, *setar*: 21 verbetes).
- Glossários de domínio: software (23 termos), dados (14), infraestrutura (14) e finanças (11).
- **PTC-08** automática para gênero: "a pipeline" gera alerta quando o glossário registra "o pipeline".
- `--dominios` restringe os glossários usados.

### Diretivas no documento (novo)

- `ptc-ignorar` e `ptc-ignorar-inicio`/`-fim`: blocos fora da verificação, como os exemplos incorretos de propósito.
- `ptc-idioma`: marca um bloco em outro idioma. Blocos em inglês também são detectados automaticamente (`--sem-deteccao-idioma` desliga).
- `ptc-mencoes: italico, aspas`: trechos citados não geram alerta de vocabulário e contam como uma palavra.
- `blocos_ignorados` na saída lista cada bloco fora da verificação, com o motivo.

### O projeto segue as próprias regras

- README, CHANGELOG, SKILL.md, spec e rubrica revisados com o PTC-BR: de 84 achados para 9, todos de voz passiva com agente irrelevante (confiança baixa).
- `tests/test_documentacao.py` impede a regressão.
- A revisão revelou 6 falsos positivos no verificador, agora corrigidos:
  - sigla definida em título ou com sufixo (*PTC-BR (Português…)*);
  - marcador de posição (*PTC-NN*);
  - "execute a aplicação" tratado como nominalização;
  - adjetivo proparoxítono (*válido*) tratado como voz passiva;
  - "muito" tratado como particípio;
  - particípio acentuado (*incluído*) não reconhecido.

### Ambiguidade

- 9 pares novos de calibração do judge: pronome com dois referentes, alcance de adjetivo, *uma vez que*, *todos… não* e grau de certeza.
- A rubrica trata a escolha silenciosa de uma leitura como informação acrescentada (Q2).
- Calibração com 27 pares: 25 de 27 vereditos na primeira rodada. Os 2 casos divergentes tinham defeito de rótulo e foram corrigidos; depois da correção, 100% em 2 execuções.
- 2 casos novos de eval: frase ambígua e probabilidade.

### Outros

- Palavra em maiúsculas (DELETE, UPDATE) não casa com verbete: é palavra-chave ou sigla.
- CI no GitHub Actions: testes sem dependências e com dependências, em Python 3.10 e 3.12.

## [plugin 0.3.0 · spec 0.3.0] — 2026-10-30

### Camadas de vocabulário do time (novo)

- `--vocabulario camada.yaml` (ou `.json`, pode repetir): o time muda verbetes do vocabulário geral (`sobrepor`), acrescenta verbetes próprios (`verbetes`) e declara siglas (`siglas`). A última camada vence.
- `exemplos/camada-time.yaml`: modelo de camada.
- `ptc_vocab.py`: flexão, regex e camadas em um módulo da skill (só biblioteca padrão). O compilador passa a usar o mesmo módulo.

### Decisões de vocabulário

- *conferir* e *rodar*: sinônimos aceitos de *verificar* e *executar* (campo novo `sinonimo_de`). A escolha final fica com a camada de cada time.
- *solicitar*: aprovado.
- *parametrizar*: aprovado, com sentido próprio (definir parâmetros de consulta, função ou modelo).

### Vocabulário: 68 → 164 verbetes

- `formal.yaml` (novo): 73 verbetes de registro formal e burocrático.
  - Verbos (*ensejar*, *possuir*, *prosseguir*) e conectivos (*outrossim*, *mediante*, *uma vez que*).
  - Padrões (introdução vazia, mesóclise), adjetivos, advérbios e substantivos (*supracitado*, *primeiramente*, *metodologia*).
- `polissemia.yaml` (novo): 23 palavras com mais de um sentido técnico, com foco em software e finanças (*taxa*, *título*, *transação*, *homologação*, *padrão*, *modelo*).
- Flexão de adjetivos (gênero e número) e plural de *-vel* (*imprescindíveis*).
- Correção: *se encontrar* (condição com o verbo *encontrar*) deixa de ser marcado como *encontrar-se*.
- O compilador mostra o arquivo e a linha quando o YAML é inválido.

### Lematização (opcional)

- `--lematizar` usa `simplemma`, se estiver instalado, para achar formas que a flexão não gera (*utilizaremos*, *efetuássemos*). Verbetes com `formas` ou `padrao` explícitos ficam fora, para evitar ambiguidade.
- `tools/medir_corpus.py` aceita `--lematizar` e `--vocabulario`.

### Qualidade

- 80 testes unitários (eram 66). Os 4 testes de lematização são pulados sem `simplemma`.
- Os 4 casos de `claude plugin eval` passaram (nota 1.00 cada).
- Licença MIT.

## [plugin 0.2.0 · spec 0.2.0] — 2026-10-30

### Vocabulário controlado (novo)

- 68 verbetes em `references/vocabulario/geral.yaml`. São 34 não preferidos, 21 palavras com mais de um sentido técnico, 8 verbos de instrução aprovados, 4 em análise e 1 proibido.
- `schema.json` (JSON Schema) e `tools/compilar_vocabulario.py`: valida os verbetes, gera a flexão (verbos regulares e plural) e compila `scripts/vocabulario.json`. O build é reprodutível.
- Nova regra **PTC-25** (vocabulário controlado). Termo proibido é violação obrigatória em qualquer perfil.
- Relatório `vocabulario_polissemico` na saída do verificador, usado na passada global da PTC-08.
- Padrões: *o mesmo* como pronome (PTC-07) e gerundismo (*vamos estar enviando*).
- Verbetes `em_analise` para decisão do time: *conferir*, *rodar*, *solicitar*, *parametrizar*.

### Verificador

- `--siglas`: lista de siglas conhecidas do público (arquivo ou lista separada por vírgula).
- Precisão medida em corpus real de documentação técnica (60 arquivos, cerca de 41 mil palavras):
  - **PTC-23:** de 136 para 36 alertas. Conta negações por oração e trata a concordância negativa (*não há X nem Y*) como uma negação.
  - **PTC-17:** de 172 para 136 alertas, 43 deles com confiança baixa. Ignora nomes de arquivo (*SKILL.md*) e marca caixa alta de ênfase (*LEIA*) com confiança baixa.
  - **PTC-12:** quantificadores (*vários*, *alguns*, *etc.*) passam a ter confiança baixa.
  - **PTC-18:** substantivos terminados em *-or* (*valor*) deixam de ser tratados como infinitivo.
  - **PTC-11:** *levar* sai dos verbos-suporte (*leva a correção para HML* é literal). Conectivos saem da PTC-11 e vão para o vocabulário (PTC-25).
- `tools/medir_corpus.py`: mede os achados por regra e confiança em qualquer pasta de `.md`.

### Especificação 0.1.1 → 0.2.0

- **Novo:** PTC-25 e seção 7 reescrita (arquivos, status, flexão).
- **Mudado:** PTC-23 define negação encadeada e concordância negativa.
- **Novo:** `--siglas` documentado na seção 6.
- Roadmap atualizado (seção 11).

### Testes

- 66 testes unitários (eram 45), incluindo um teste por verbete: o exemplo incorreto dispara e o correto não.

## [plugin 0.1.0 · spec 0.1.1] — 2026-10-30

### Plugin (novo)

- Estrutura de plugin do Claude Code com `plugin.json` e `marketplace.json`.
- Skill `ptc-br` com os modos revisar, reescrever e verificar, e o fluxo em cinco passos.
- `ptc_check.py`: verificador das regras PTC-03, 04, 05, 11, 12, 15, 17, 18, 21, 23 e 24, com perfis L/T/C, exceções e siglas declaradas.
- `ptc_diff.py`: checagem de preservação de números, negações, restrições, condições, alternativas, comparadores e modais.
- Rubrica do judge com perguntas binárias Q1–Q6 e saída JSON.
- 45 testes unitários, 18 pares de calibração do judge e 4 casos de `claude plugin eval`.
- Calibração do judge: concordância no veredito de 71% → 97% (2 execuções × 18 pares).
  - O ganho veio da correção dos rótulos e de três ajustes na rubrica.
  - Ajustes: Q5 para PTC-06, Q6 com a lista de regras obrigatórias e alcance de condições em frases divididas.

### Especificação 0.1.0 → 0.1.1

- **Corrigido:** o exemplo 8.2 acrescentava "três" e "competição", informações ausentes do original. O exemplo antigo virou "reescrita a evitar".
- **Corrigido (achado pelo judge):** as reescritas "corretas" de 8.1, 8.2 e 8.3 mudavam a finalidade, deslocavam uma restrição ou mantinham a condição depois da ação.
- **Corrigido:** o exemplo 8.1 trocava "fora do período de validade" por "expirado", o que reduz o escopo. O exemplo antigo virou "reescrita a evitar".
- **Novo:** tipo de verificação por regra: (A) automática, (P) parcial, (J) julgamento.
- **Novo:** matriz regra × perfil (seção 3.1). Os perfis PTC-L e PTC-C passam a ter efeito.
- **Novo:** regras de contagem de palavras e de frases (seção 5).
- **Novo:** sintaxe de exceções e de siglas conhecidas (seção 6).
- **Novo:** política de versionamento (seção 10) e roadmap revisado (seção 11).
- **Mudado:** a PTC-08 incorpora a PTC-09. A PTC-09 fica marcada como *[REMOVIDA]*, e o ID não é reutilizado.
- **Mudado:** a PTC-01 e a PTC-05 têm critérios mais objetivos; a PTC-22 proíbe acrescentar informação.
- **Mudado:** o exemplo de verbete guarda o lema, não a lista de formas flexionadas.
