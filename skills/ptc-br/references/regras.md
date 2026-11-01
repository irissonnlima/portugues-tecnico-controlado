# PTC-BR — Português Técnico Controlado

<!-- ptc-mencoes: italico -->

- **Versão:** 0.4.0 (especificação experimental)
- **Status:** rascunho para discussão
- **Idioma:** português brasileiro (pt-BR)
- **Referências conceituais:** a linguagem simples da ABNT NBR ISO 24495-1 e a linguagem controlada ASD-STE100 (Simplified Technical English)

> **Natureza deste documento:** proposta independente. Ela não é norma da ABNT nem tradução do ASD-STE100, e não declara conformidade com esses documentos. Os limites numéricos e as listas de palavras são decisões experimentais deste projeto.

## 1. Objetivo

O PTC-BR define regras para escrever textos técnicos claros, consistentes e sem ambiguidade desnecessária. O público-alvo são instruções, especificações de software, manuais, relatórios e comunicações de engenharia.

**Princípio central:** cada frase transmite uma informação identificável. O leitor sabe quem executa cada ação, a que objeto cada palavra se refere e qual condição vale para cada ação.

## 2. Como ler as regras

Cada regra tem um **ID**, um **nível** e um **tipo de verificação**.

**Nível** (no perfil padrão PTC-T):

- **[OBRIGATÓRIA]** — uma violação torna o texto *Não conforme*, salvo exceção registrada (seção 6).
- **[RECOMENDADA]** — uma violação gera sugestão, não reprova o texto.

**Tipo de verificação:**

- **(A) automática** — um script detecta a violação com boa precisão.
- **(P) parcial** — um script sinaliza candidatos; uma pessoa ou o modelo confirma.
- **(J) julgamento** — só uma leitura contextual decide.

**Estabilidade dos IDs:** um ID nunca é reutilizado. Uma regra removida continua listada com a marca *[REMOVIDA]*.

## 3. Perfis de aplicação

| Perfil | Uso | Grau de controle |
|---|---|---|
| **PTC-L** (leve) | E-mails, mensagens e comunicação interna | Clareza e consistência; limites flexíveis |
| **PTC-T** (técnico) | Relatórios, requisitos e documentação de software | Regras estruturais e terminologia controlada |
| **PTC-C** (crítico) | Procedimentos operacionais e instruções de segurança | Regras obrigatórias; exceções documentadas |

O **PTC-T** é o perfil padrão. Os perfis não são níveis de certificação.

### 3.1. Matriz regra × perfil

O nível de cada regra muda conforme o perfil. **O** = obrigatória, **R** = recomendada, **—** = não se aplica.

| Regra | PTC-L | PTC-T | PTC-C |
|---|---|---|---|
| PTC-01 Ordem direta | R | O | O |
| PTC-02 Uma ação por frase | R | O | O |
| PTC-03 Instrução ≤ 20 palavras | R | O | O |
| PTC-04 Descrição ≤ 25 palavras | — | R | O |
| PTC-05 Voz ativa | R | O | O |
| PTC-06 Condição antes da ação | O | O | O |
| PTC-07 Pronome sem ambiguidade | O | O | O |
| PTC-08 Termo consistente | R | O | O |
| PTC-10 Glossário por domínio | — | O | O |
| PTC-11 Verbo direto | R | R | O |
| PTC-12 Sem expressão vaga | R | R | O |
| PTC-13 Preservar termo técnico | O | O | O |
| PTC-14 Um assunto por parágrafo | R | O | O |
| PTC-15 Parágrafo ≤ 6 frases | — | R | O |
| PTC-16 Listas | R | R | R |
| PTC-17 Sigla definida | R | O | O |
| PTC-18 Imperativo em passos | R | O | O |
| PTC-19 Unidades e limites | O | O | O |
| PTC-20 Separar comando, condição, resultado e aviso | — | O | O |
| PTC-21 Risco explícito | O | O | O |
| PTC-22 Preservar sentido | O | O | O |
| PTC-23 Sem subordinação excessiva | R | R | O |
| PTC-24 Exceção registrada | — | O | O |
| PTC-25 Vocabulário controlado | R | R | O |
| PTC-26 Probabilidade com percentual | R | O | O |

## 4. Regras de escrita

### 4.1. Estrutura de frases

- **PTC-01 [OBRIGATÓRIA] (J)** — Use a ordem direta (*sujeito + verbo + complemento*). Inverta a ordem só para pôr a condição antes da ação (PTC-06).
- **PTC-02 [OBRIGATÓRIA] (J)** — Em procedimentos, escreva **uma ação por frase**. Ações inseparáveis podem aparecer juntas: *Pressione e segure o botão.*
- **PTC-03 [OBRIGATÓRIA] (A)** — Limite instruções a **20 palavras** (contagem na seção 5). Se o limite comprometer o sentido, divida a instrução ou registre uma exceção (PTC-24).
- **PTC-04 [RECOMENDADA] (A)** — Limite frases descritivas a **25 palavras**.
- **PTC-05 [OBRIGATÓRIA] (P)** — Use a voz ativa quando o texto conhece o agente da ação. A voz passiva é aceita quando o agente é desconhecido ou irrelevante para o leitor.
- **PTC-06 [OBRIGATÓRIA] (J)** — Escreva a condição antes da ação que depende dela.
- **PTC-07 [OBRIGATÓRIA] (J)** — Não use pronomes (*ele*, *ela*, *isso*, *esse*) quando o referente admitir mais de uma interpretação. Repita o substantivo.

### 4.2. Vocabulário e terminologia

- **PTC-08 [OBRIGATÓRIA] (P)** — Use um termo para cada conceito e um sentido para cada termo, dentro do documento e do domínio. *Incorpora a antiga PTC-09.*
- **PTC-09 [REMOVIDA em 0.1.1]** — Conteúdo incorporado à PTC-08.
- **PTC-10 [OBRIGATÓRIA] (P)** — Use os termos técnicos do glossário do domínio. Enquanto o glossário do domínio não existir, defina os termos no próprio documento.
- **PTC-11 [RECOMENDADA] (A)** — Prefira verbos diretos a locuções com substantivos abstratos: *verificar*, em vez de *realizar uma verificação*.
- **PTC-12 [RECOMENDADA] (A)** — Substitua expressões vagas por um critério: *adequado*, *rapidamente*, *em breve*, *quando possível*, *normalmente*.
- **PTC-13 [OBRIGATÓRIA] (J)** — Não substitua um termo técnico preciso por uma palavra mais simples quando isso mudar o significado.

### 4.3. Parágrafos e organização

- **PTC-14 [OBRIGATÓRIA] (J)** — Trate um assunto principal por parágrafo.
- **PTC-15 [RECOMENDADA] (A)** — Limite cada parágrafo a **seis frases**.
- **PTC-16 [RECOMENDADA] (J)** — Use listas para conjuntos de condições, opções e etapas independentes.
- **PTC-17 [OBRIGATÓRIA] (P)** — Defina cada sigla na primeira ocorrência: *Interface de Programação de Aplicações (API)*. Siglas declaradas como conhecidas do público são isentas (seção 6).

### 4.4. Instruções, medidas e riscos

- **PTC-18 [OBRIGATÓRIA] (P)** — Use o imperativo em passos operacionais: *Selecione*, *Confirme*, *Verifique*.
- **PTC-19 [OBRIGATÓRIA] (J)** — Especifique unidades, limites e condições de medição quando forem relevantes.
- **PTC-20 [OBRIGATÓRIA] (J)** — Separe comandos, pré-condições, resultados esperados e avisos de segurança.
- **PTC-21 [OBRIGATÓRIA] (P)** — Descreva o risco e a consequência de modo explícito. Não use só *Atenção* ou *Importante* como substituto.

### 4.5. Qualidade e revisão

- **PTC-22 [OBRIGATÓRIA] (P)** — Ao reescrever, preserve números, operadores, negações, restrições (*só*, *exceto*), condições e relações de causa e efeito. Use **só** a informação que o original contém.
- **PTC-23 [RECOMENDADA] (P)** — Reescreva frases com três ou mais orações subordinadas. Reescreva também negações encadeadas na mesma oração: *Não é possível não validar*; *Nunca entregue X sem Y*.
  - A concordância negativa (*não há X nem Y*, *não precisa de nada*) conta como **uma** negação.
  - O verificador avalia cada oração coordenada em separado (*não resolve e não tem rota*).
- **PTC-24 [OBRIGATÓRIA] (A)** — Registre exceções justificadas às regras obrigatórias (seção 6), em vez de alterar o sentido em silêncio.
- **PTC-25 [RECOMENDADA] (A)** — Use o termo preferido do vocabulário controlado (seção 7). Um termo com status *proibido* é violação obrigatória em qualquer perfil.

### 4.6. Probabilidade e certeza

- **PTC-26 [OBRIGATÓRIA] (A)** — Expresse probabilidade só com os termos da escala abaixo. Escreva a faixa percentual entre parênteses logo depois do termo, em toda ocorrência: *A causa provável (55–80%) é o certificado.* O número informado precisa caber na faixa do termo.

| Termo | Faixa | Termo | Faixa |
|---|---|---|---|
| quase impossível | 1–5% | provável | 55–80% |
| muito improvável | 5–20% | muito provável | 80–95% |
| improvável | 20–45% | quase certo | 95–99% |
| chance equilibrada | 45–55% | | |

- A escala segue a Intelligence Community Directive 203 (ICD 203), padrão de 2015 da comunidade de inteligência dos EUA. Esse padrão atualiza a tabela *Words of Estimative Probability*, de Sherman Kent (CIA, 1964).
- Formas derivadas seguem a faixa do termo: *provavelmente* (55–80%), *quase certamente* (95–99%), *provavelmente não* (20–45%).
- Expressões vagas (*talvez*, *possivelmente*, *é possível que*, *certamente*, *dificilmente*, *grande chance*) não têm faixa. Troque por um termo da escala.
- Para um fato determinístico (regra do sistema, limite configurado), afirme o fato, sem termo de probabilidade: *O token expira em 1 h.*
- O percentual serve de checagem cruzada: o verificador aponta o termo sem percentual e o número fora da faixa (*muito provável (60%)*).

## 5. Regras de contagem

Estas regras valem para PTC-03, PTC-04 e PTC-15.

**Palavra** é uma sequência separada por espaços, com estas decisões:

| Caso | Exemplo | Conta como |
|---|---|---|
| Palavra composta com hífen | *guarda-chuva* | 1 |
| Ênclise e mesóclise | *renove-o* | 1 |
| Contração | *do*, *na*, *pelo* | 1 |
| Número com unidade | *20 mV*, *1,5 s*, *30 %* | 1 |
| Identificador de norma | *ABNT NBR ISO 24495-1* | 1 |
| Código, comando ou caminho entre crases | `` `kubectl get pods` `` | 1 |
| URL | *https://exemplo.com/a* | 1 |
| Pontuação isolada | *—*, *–*, *-* | 0 |

**Frase** termina em `.`, `!` ou `?` seguido de espaço ou do fim do bloco. Estes casos **não** terminam frase:

- abreviações: *ex.*, *p. ex.*, *Sr.*, *Sra.*, *Dr.*, *nº*, *art.*, *fig.*, *pág.*, *aprox.*, *máx.*, *mín.*, *obs.*, *etc.* no meio da frase, *e.g.*, *i.e.*;
- números decimais e versões: *1.5*, *v2.1.0*.

**Item de lista:** cada item conta como uma frase. O verificador trata um item de **lista numerada** como **instrução** (limite da PTC-03) e os demais blocos como **descrição** (limite da PTC-04).

**Menção:** com a diretiva `ptc-mencoes` (seção 6), cada trecho citado conta como uma palavra.

**Fora da contagem:** títulos, blocos de código, tabelas e comentários HTML.

## 6. Exceções, siglas e diretivas

Registre uma exceção com um comentário HTML **na linha anterior** ao bloco afetado:

```markdown
<!-- ptc-excecao: PTC-03; motivo: o nome do parâmetro não pode ser dividido -->
1. Defina o parâmetro `max_connections_per_host_when_proxy_is_enabled` com o valor 10 antes de iniciar o serviço principal.
```

Declare siglas conhecidas do público, uma vez por documento:

```markdown
<!-- ptc-siglas: API, SQL, HTTP -->
```

Para um time ou domínio inteiro, passe a lista ao verificador: `ptc_check.py arquivo.md --siglas siglas.txt` (uma sigla por linha) ou `--siglas "DDL,HML"`. Um título também define a sigla: `# PTC-BR — Português Técnico Controlado`.

### 6.1. Diretivas de bloco

| Diretiva | Efeito |
|---|---|
| `<!-- ptc-ignorar: motivo -->` | O bloco seguinte fica fora da verificação. Use para exemplos incorretos de propósito. |
| `<!-- ptc-ignorar-inicio: motivo -->` … `<!-- ptc-ignorar-fim -->` | A região inteira fica fora da verificação. |
| `<!-- ptc-idioma: en -->` | O bloco seguinte está em outro idioma e fica fora da verificação. |
| `<!-- ptc-idioma-inicio: en -->` … `<!-- ptc-idioma-fim -->` | A região inteira está em outro idioma. |
| `<!-- ptc-mencoes: italico, aspas -->` | Vale para o documento. Trechos em itálico ou entre aspas são **menções** a um termo, não uso. A menção não gera alerta de vocabulário e conta como uma palavra. |

O verificador também **detecta blocos em inglês** pelas palavras funcionais (*the*, *of*, *is*) e os deixa fora da verificação. Termos técnicos em inglês dentro de uma frase em português não mudam o idioma do bloco. A opção `--sem-deteccao-idioma` desliga a detecção.

Todo bloco fora da verificação aparece em `blocos_ignorados`, com a linha e o motivo.

## 7. Vocabulário controlado

O objetivo **não** é limitar toda a língua portuguesa a 900 palavras. A proposta separa:

1. **Vocabulário geral:** palavras de uso frequente, com significado e classe gramatical definidos.
2. **Termos técnicos por domínio:** palavras necessárias para descrever conceitos de engenharia, software, direito ou outras áreas.
3. **Nomes próprios e identificadores:** nomes de produtos, campos, APIs, normas e equipamentos, tratados separadamente.

Um vocabulário de produção exige validação linguística, análise de corpus e participação dos especialistas do domínio.

### 7.1. Arquivos e status

O vocabulário fica em `references/vocabulario/*.yaml` (`geral.yaml`, `formal.yaml`, `polissemia.yaml`), um verbete por entrada, validado por `references/vocabulario/schema.json`. O verificador usa a versão compilada (`scripts/vocabulario.json`), gerada por `tools/compilar_vocabulario.py`.

| Status | Efeito no verificador |
|---|---|
| `aprovado` | Nenhum alerta. Documenta o sentido aprovado. |
| `nao_preferido` | Alerta PTC-25, confiança média, com o termo a preferir. |
| `proibido` | Alerta PTC-25 obrigatório, confiança alta, em qualquer perfil. |
| `em_analise` | Alerta PTC-25, confiança baixa. Indica uma decisão pendente do time. |

Um verbete **aprovado com `sinonimo_de`** é um sinônimo aceito: *verificar* e *conferir*, *executar* e *rodar*. O vocabulário geral aceita os dois; a camada do time escolhe um (seção 7.3).

Um verbete **aprovado com `sentidos`** descreve uma palavra com mais de um sentido técnico (*subir*, *base*, *chave*). Ela não gera alerta; aparece no relatório `vocabulario_polissemico` para a revisão da PTC-08.

**Flexão:** o verbete guarda o lema. O compilador gera as formas de verbos regulares em *-ar*, *-er* e *-ir*, o gênero e o número de adjetivos e o plural de substantivos. Verbos irregulares, pronominais e palavras ambíguas declaram `formas`; construções declaram `padrao` (expressão regular).

### 7.3. Camadas de vocabulário do time

Um time adapta o vocabulário sem alterar o PTC-BR. A camada é um arquivo YAML ou JSON com três partes opcionais:

- `sobrepor`: muda o status, `preferir` ou `motivo` de verbetes existentes, por `id` ou `lema`;
- `verbetes`: acrescenta verbetes com o mesmo schema, com um prefixo de ID próprio (ex.: `T-0001`);
- `siglas`: siglas conhecidas do público do time.

```bash
ptc_check.py doc.md --vocabulario camada-do-time.yaml
```

**Precedência:** a última camada passada vence; qualquer camada vence o vocabulário geral. Exemplo completo: `exemplos/camada-time.yaml`.

### 7.4. Lematização (opcional)

Com `--lematizar` e a biblioteca `simplemma` instalada, o verificador também acha formas que a flexão automática não gera (*utilizaremos*, *efetuássemos*). Verbetes com `formas` ou `padrao` explícitos não usam lematização: nesses casos o autor restringiu as formas para evitar ambiguidade (*auxiliar* como adjetivo).

### 7.5. Anglicismos

- **Substantivos técnicos consolidados** (*commit*, *branch*, *pipeline*, *query*) são aprovados nos glossários de domínio. Escreva-os **sem itálico**: eles são vocabulário da área, não palavras estrangeiras ocasionais.
- O glossário registra o **gênero** de cada termo (*o commit*, *a branch*, *o pipeline*, *a query*). O verificador aponta o gênero oposto (PTC-08).
- **Verbos aportuguesados** (*commitar*, *deployar*, *setar*, *startar*) são não preferidos. Use o verbo em português ou *fazer + substantivo*: *faça commit*, *publique*, *defina*, *inicie*.
- Um time que prefira o termo em português (*implantação* em vez de *deploy*) registra a escolha na camada dele (seção 7.3).

### 7.6. Glossários de domínio

Os glossários ficam em `references/glossarios/`: `software.yaml`, `dados.yaml`, `infraestrutura.yaml` e `financas.yaml`. Cada termo tem definição, domínio e, para anglicismos, gênero. A opção `--dominios software,dados` restringe os glossários usados; o padrão é usar todos.

### 7.7. Amostra

| Prefira | Evite quando desnecessário | Observação |
|---|---|---|
| usar | utilizar, fazer uso de | *Utilizar* não é errado; busca-se consistência. |
| iniciar | dar início a | Verbo direto. |
| terminar | finalizar, concluir a execução de | Escolha um termo conforme o evento real. |
| verificar | realizar a verificação de | Verbo direto. |
| enviar | efetuar o envio de | Verbo direto. |
| mudar | proceder à alteração de | Em contexto formal, *alterar* também pode ser aceito. |
| porque | tendo em vista que | Explicite causa quando houver uma relação causal. |
| antes | previamente a | Preferência de clareza. |
| depois | subsequentemente a | Preferência de clareza. |
| se | na hipótese de que | Use quando expressar uma condição. |

**Não proibir automaticamente:** *otimização*, *algoritmo genético*, *envergadura*, *centro de gravidade*, *certificado digital*, *autenticação* e *assinatura criptográfica*. São termos técnicos legítimos quando usados com precisão.

### Exemplo de verbete

O verbete guarda o **lema**, não a lista de formas flexionadas. O verificador trata a flexão.

```yaml
id: V-0001
lema: verificar
classe: verbo
significado_aprovado: examinar um estado ou resultado para determinar se atende a um critério
preferida_em_instrucoes: verifique
termos_nao_preferidos: [realizar a verificação de, proceder à checagem de]
exemplo_correto: Verifique a versão do certificado.
exemplo_incorreto: Realize a verificação da versão do certificado.
status: aprovado            # aprovado | nao_preferido | proibido | em_analise
versao_inclusao: 0.1.0
```

## 8. Exemplos de reescrita

### 8.1. Procedimento de software

**Antes:**

<!-- ptc-ignorar: exemplo do texto original, com os problemas que a seção corrige -->
> Quando o certificado utilizado para a autenticação encontrar-se fora do seu período de validade, deverá ser realizado o procedimento de renovação para possibilitar a continuidade da operação.

**Depois (PTC-T):**

> Se o certificado de autenticação estiver fora do período de validade, renove o certificado para continuar a operação.

**Motivo:** a condição vem antes da ação; o comando é explícito; a finalidade (*continuar a operação*) é mantida; o termo *certificado* é consistente.

**Reescrita a evitar:** *… renove o certificado. Depois, execute a operação novamente.* — *Executar de novo* não é o mesmo que *continuar*: a reescrita troca a finalidade por uma ação nova (PTC-22).

**Reescrita a evitar:** *Se o certificado estiver expirado, renove o certificado.* — *Expirado* exclui o certificado que **ainda não** entrou no período de validade. A reescrita reduz o escopo da condição (PTC-22).

### 8.2. Engenharia aeroespacial

**Antes:**

<!-- ptc-ignorar: exemplo do texto original, com os problemas que a seção corrige -->
> O presente estudo objetiva proceder à comparação de metodologias estocásticas aplicadas à maximização do desempenho de configurações aeronáuticas sujeitas a alterações regulamentares.

**Depois (PTC-T):**

> Este estudo compara métodos estocásticos usados para maximizar o desempenho de configurações de aeronaves sujeitas a alterações de regulamento.

**Motivo:** verbo direto (*compara*) e menos substantivos abstratos, sem eliminar os termos técnicos essenciais. A restrição *sujeitas a alterações* continua ligada às *configurações*.

**Reescrita a evitar (1):** *… configurações de aeronaves. A comparação considera mudanças no regulamento.* — A divisão desloca a restrição das configurações para a comparação e cria uma afirmação que o original não faz (PTC-22).

**Reescrita a evitar (2):** *Este estudo compara três algoritmos de otimização estocástica usados no projeto de aeronaves. A comparação considera as mudanças nas regras da competição.* — O original não informa a **quantidade** de métodos nem cita uma **competição**. A reescrita acrescenta informação (PTC-22).

### 8.3. Preservação de significado

**Original:**

> O sistema só aprova a assinatura quando o certificado é válido e não está revogado.

**Reescrita incorreta:**

<!-- ptc-ignorar: exemplo de reescrita incorreta -->
> O sistema aprova a assinatura quando o certificado é válido.

**Reescrita correta:**

> Somente se o certificado estiver válido **e** não estiver revogado, o sistema aprova a assinatura.

**Motivo:** a reescrita incorreta elimina a restrição *só* e a condição *não está revogado*. A reescrita correta mantém as duas e põe a condição antes da ação (PTC-06).

## 9. Verificação de conformidade

| Verificação | Regras | Tipo | Ferramenta |
|---|---|---|---|
| Contagem de palavras por frase | PTC-03, PTC-04 | A | `ptc_check.py` |
| Contagem de frases por parágrafo | PTC-15 | A | `ptc_check.py` |
| Locuções com substantivo abstrato | PTC-11 | A | `ptc_check.py` |
| Expressões vagas | PTC-12 | A | `ptc_check.py` |
| Siglas sem definição | PTC-17 | P | `ptc_check.py` |
| Vocabulário controlado | PTC-25, PTC-07 | A | `ptc_check.py` + `vocabulario.json` |
| Palavras com mais de um sentido | PTC-08 | P | relatório `vocabulario_polissemico` + revisão |
| Gênero dos termos do glossário | PTC-08 | A | `ptc_check.py` + glossários |
| Probabilidade com percentual coerente | PTC-26 | A | `ptc_check.py` |
| Grau de certeza preservado na reescrita | PTC-22, PTC-26 | A | `ptc_diff.py` |
| Voz passiva analítica | PTC-05 | P | `ptc_check.py` + revisão |
| Aviso sem consequência | PTC-21 | P | `ptc_check.py` + revisão |
| Negações e subordinadas encadeadas | PTC-23 | P | `ptc_check.py` + revisão |
| Números, negações e restrições preservados | PTC-22 | P | `ptc_diff.py` + judge |
| Informação acrescentada ou escopo alterado | PTC-22 | J | judge |
| Pronomes, ordem, um assunto por parágrafo | PTC-01, 07, 14 | J | revisão |

**Classificação:**

- **Conforme:** nenhuma regra obrigatória violada e termos técnicos justificados.
- **Conforme com exceções:** desvios obrigatórios registrados conforme a seção 6.
- **Não conforme:** pelo menos uma violação obrigatória sem exceção registrada.

Isso mede apenas a conformidade **interna ao PTC-BR**, não a conformidade com a ABNT ou com o ASD-STE100.

## 10. Versionamento

A especificação usa versionamento semântico, separado da versão do plugin:

- **major:** remover ou renumerar uma regra, ou subir uma regra de RECOMENDADA para OBRIGATÓRIA no perfil PTC-T;
- **minor:** nova regra, novo verbete, novo glossário ou nova verificação;
- **patch:** correção de exemplo, de texto ou de redação sem mudança de regra.

Antes da 1.0.0, mudanças incompatíveis podem ocorrer em versões minor e ficam registradas no CHANGELOG.

## 11. Próximas versões

- **0.2.0:** vocabulário controlado com 68 verbetes, schema validado e flexão automática; regra PTC-25; PTC-23 com concordância negativa; precisão do verificador medida em corpus real.
- **0.3.0:** camadas de vocabulário do time; sinônimos aceitos; 164 verbetes; lematização opcional.
- **0.4.0 (atual):** escala de probabilidade (PTC-26) e política de anglicismos.
  - Glossários de software, dados, infraestrutura e finanças, com gênero.
  - Diretivas de idioma, de menção e de bloco ignorado.
  - Casos de ambiguidade e documentação do projeto revisada com o PTC-BR.
- **0.5.0–0.9.0:** uso real; taxa de aceitação por regra; ajustes.
- **1.0.0:** IDs estáveis; teste de compreensão com leitores; licença e governança definidas.

---

**Licença:** MIT (arquivo `LICENSE` na raiz do repositório). **Governança:** ainda não definida. Este protótipo é material de trabalho para debate e revisão.
