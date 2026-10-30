---
name: ptc-br
description: Revisa, reescreve e verifica textos técnicos em português segundo o PTC-BR (Português Técnico Controlado), um padrão de linguagem controlada inspirado no ASD-STE100 e na linguagem simples (ISO 24495-1). Use quando pedirem "revise em PTC", "português técnico controlado", "linguagem controlada", "simplifique este texto técnico", "deixe o procedimento mais claro", "verifique a conformidade PTC", ou ao revisar manuais, procedimentos, requisitos, relatórios e documentação técnica em pt-BR. Use também para conferir se uma reescrita preservou o sentido do original. Se o time tiver uma skill de escrita própria, combine as duas: ela acrescenta o vocabulário e as siglas do domínio.
argument-hint: "[revisar|reescrever|verificar] <arquivo> [perfil L|T|C]"
---

# PTC-BR — Português Técnico Controlado

Esta skill aplica a especificação em `${CLAUDE_SKILL_DIR}/references/regras.md` (versão 0.2.0).
Leia a spec quando precisar do texto exato de uma regra, da matriz de perfis (seção 3.1) ou das regras de contagem (seção 5).

## Modos

| Modo | Pedido típico | Entrega |
|---|---|---|
| **revisar** (padrão) | "revise este texto em PTC" | Relatório de achados + classificação. **Não** altera o texto. |
| **reescrever** | "reescreva", "simplifique", "corrija" | Diff mínimo: só as frases com achado. Cada par passa pelo judge. |
| **verificar** | "esta reescrita mantém o sentido?" | Veredito do judge para cada par original → reescrita. |

**Perfil:** PTC-T, salvo pedido explícito. Use PTC-C para procedimentos de operação e segurança, e PTC-L para e-mail e mensagem.

## Fluxo

### 1. Verificação automática (arquivo inteiro)

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ptc_check.py <arquivo> --perfil T --json
```

Para texto colado no chat, use `--texto "..."`. Se o time tiver uma lista de siglas conhecidas, passe `--siglas arquivo.txt` (ou `--siglas "SIGLA1,SIGLA2"`). O script cobre as regras (A) e (P), inclusive o vocabulário controlado (PTC-25). Ele **não** decide sozinho:

- confiança `alta`: trate como violação, salvo erro evidente do script;
- confiança `media` ou `baixa`: confirme lendo a frase. Descarte o falso positivo e registre o motivo em uma linha;
- PTC-25 com status `em_analise` (confiança baixa): não trate como violação. Cite o termo uma vez no relatório, como decisão pendente do vocabulário.

### 2. Passada global (arquivo inteiro)

Leia o documento inteiro uma vez e monte um **inventário de termos**: cada conceito, o termo usado e as variações encontradas. Comece pelo campo `vocabulario_polissemico` da saída do script: ele lista as palavras com mais de um sentido técnico, as linhas e os sentidos possíveis. Para cada uma, confira se o documento usa **um único** sentido; se usar dois (*subir* = publicar e *subir* = enviar), sugira o termo sem ambiguidade de cada sentido. Use o inventário para:

- **PTC-08:** o mesmo conceito com nomes diferentes (*servidor* × *host* × *máquina*);
- **PTC-17:** siglas que o script não pegou (minúsculas, com acento);
- **PTC-07:** pronomes cujo referente está em outra frase.

Em documentos grandes, faça a passada global uma vez e use o inventário como contexto na passada local.

### 3. Passada local (por seção ou parágrafo)

Avalie as regras de julgamento (J): PTC-01, 02, 06, 07, 13, 14, 16, 19 e 20. Confirme ou descarte os achados `media` e `baixa` do passo 1.

### 4. Reescrita (só no modo reescrever)

- Reescreva **somente** as frases com achado confirmado. Não reescreva o texto inteiro: cada frase alterada sem necessidade é um risco de mudar o sentido (PTC-22).
- Mantenha termos técnicos, nomes, identificadores, código e números exatamente como estão.
- Não acrescente nada que o original não diga. Se a frase original for ambígua, **pergunte** ou marque `[ambíguo: …]`. Não escolha uma interpretação em silêncio.
- Se a regra não puder ser cumprida sem perda de sentido, mantenha a frase e sugira uma exceção (seção 6 da spec).

### 5. Judge (cada par original → reescrita)

Antes de entregar, rode a checagem determinística de preservação:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/ptc_diff.py --original "<original>" --reescrita "<reescrita>" --json
```

Para vários pares, grave um JSONL (`{"id", "original", "reescrita"}` por linha) e use `--pares arquivo.jsonl`.

Depois, aplique a rubrica de `${CLAUDE_SKILL_DIR}/references/rubrica-judge.md` a cada par. Avalie como um revisor independente: procure o que a reescrita perdeu ou acrescentou, não confirme o próprio trabalho. Se o par for reprovado por Q1–Q4, refaça a reescrita a partir do original.

## Formato de saída

**Modo revisar:**

```markdown
**Classificação:** Não conforme · perfil PTC-T · 3 obrigatórias, 4 recomendadas

| Linha | Regra | Nível | Trecho | Problema | Sugestão |
|---|---|---|---|---|---|
| 12 | PTC-03 | O | "Selecionar o arquivo…" | 24 palavras (máx. 20) | Dividir em dois passos |

**Inventário de termos:** servidor (×5), host (×2) → padronizar em "servidor".
**Descartados:** L30 PTC-05 "é dado" (adjetivo, não passiva).
```

**Modo reescrever:** a tabela acima com uma coluna *Reescrita*, mais o veredito do judge por linha. Para editar um arquivo, aplique as mudanças frase a frase e liste as linhas alteradas.

**Modo verificar:** o JSON da rubrica para cada par e um resumo de uma linha.

## Classificação

- **Conforme:** nenhuma obrigatória violada.
- **Conforme com exceções:** as obrigatórias violadas têm exceção registrada (`<!-- ptc-excecao: ... -->`).
- **Não conforme:** pelo menos uma obrigatória sem exceção.

O script dá só uma classificação **preliminar**. A classificação final inclui as regras de julgamento.

## Limites

- O PTC-BR é uma proposta experimental. Não declare conformidade com a ABNT NBR ISO 24495-1 nem com o ASD-STE100.
- Títulos, código, tabelas e citações literais de terceiros ficam fora da reescrita.
- Glossários de domínio ainda não existem (previstos para a 0.4.0). Enquanto isso, o inventário de termos do próprio documento e a lista `--siglas` fazem esse papel.
- O vocabulário está em `references/vocabulario/geral.yaml`. Para consultar um verbete, procure pelo lema ou pelo ID citado no alerta (ex.: V-0100).
