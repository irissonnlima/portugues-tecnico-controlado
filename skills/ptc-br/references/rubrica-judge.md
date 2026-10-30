# Rubrica do judge — PTC-BR 0.1.1

O judge avalia **um par**: o trecho original e a reescrita. Ele responde perguntas binárias com evidência. Ele **não** dá nota de 1 a 10.

Use esta rubrica em dois momentos:

1. **Na skill (passo 5):** depois de reescrever, avalie cada par antes de entregar.
2. **Na calibração:** `tests/judge/calibrar.py` compara as respostas do judge com rótulos humanos.

## Entradas

- `original` — o trecho original (frase ou parágrafo).
- `reescrita` — o trecho reescrito.
- `contexto` — o parágrafo ao redor ou o inventário de termos do documento (opcional).
- `regras_alvo` — as regras que motivaram a reescrita (ex.: `PTC-03, PTC-11`).
- `diff` — a saída de `ptc_diff.py --json` para o par (opcional, recomendado).

## Perguntas

Responda cada pergunta com `true` ou `false` e cite o trecho que comprova a resposta. Quando a resposta for `false`, a evidência pode ficar vazia.

| ID | Pergunta | Resposta que aprova |
|---|---|---|
| **Q1** | A reescrita **remove** uma condição, negação, restrição (*só*, *exceto*), número, unidade, alternativa (*ou*) ou relação de causa? | `false` |
| **Q2** | A reescrita **acrescenta** informação que o original não contém (quantidade, entidade, contexto, causa, prazo)? | `false` |
| **Q3** | A reescrita **muda o escopo** de um termo, ampliando ou reduzindo o conjunto de casos (ex.: *fora da validade* → *expirado*)? | `false` |
| **Q4** | A reescrita **troca um termo técnico preciso** por uma palavra mais vaga ou com outro sentido (PTC-13)? | `false` |
| **Q5** | A reescrita **corrige** as violações de `regras_alvo`? | `true` |
| **Q6** | A reescrita **cria** uma nova violação de regra obrigatória do perfil? | `false` |

**Responda todas as perguntas**, mesmo depois de encontrar um motivo de reprovação. Cada pergunta é medida separadamente.

**Q6 — regras obrigatórias no perfil PTC-T:** PTC-01, 02, 03, 05, 06, 07, 08, 10, 13, 14, 17, 18, 19, 20, 21, 22, 24. Para os perfis L e C, veja a seção 3.1 da spec. Exemplos frequentes: sigla nova sem definição (PTC-17), voz passiva com agente conhecido (PTC-05), instrução com mais de 20 palavras (PTC-03), duas ações na mesma frase de um procedimento (PTC-02).

**Escopo de condições em frases divididas:** quando uma frase com condição vira várias, confira se **todas** as ações que dependiam da condição continuam dependentes dela. *Se X, faça A e B* → *Se X, faça A. Faça B.* tira B do alcance da condição (Q1).

**Como usar o `diff`:** cada alerta `alta` do diff é um candidato a Q1 ou Q2, não uma resposta pronta. Confirme lendo o texto. A troca de *quando* por *se* mantém a condição. A troca de *deverá ser feito* pelo imperativo mantém a obrigação.

**Pontos de atenção:**

- Q2 inclui números por extenso (*três*), nomes de eventos, sistemas ou organizações e causas que o original não cita.
- Q3 cobre hiperônimos e hipônimos: *dispositivo* → *celular*, *usuários autorizados* → *usuários*.
- Dividir uma frase em duas **não** é perda (Q1), desde que a relação entre as partes continue explícita (*Depois*, *Se*, *Por isso*) e o alcance das condições não mude.
- Trocar a finalidade por outra ação é perda e adição: *para continuar a operação* → *execute a operação novamente*.

## Veredito

```
aprovado = not Q1 and not Q2 and not Q3 and not Q4 and Q5 and not Q6
```

- `aprovado` → entregue a reescrita.
- `reprovado` por Q1–Q4 → refaça a reescrita a partir do original. **Não** corrija a reescrita reprovada.
- `reprovado` só por Q5 ou Q6 → ajuste a reescrita e avalie de novo.

## Formato de saída

Responda **somente** com um objeto JSON válido, sem texto antes ou depois:

```json
{
  "Q1": {"resposta": false, "evidencia": ""},
  "Q2": {"resposta": true,  "evidencia": "acrescenta 'três' e 'competição', ausentes no original"},
  "Q3": {"resposta": false, "evidencia": ""},
  "Q4": {"resposta": false, "evidencia": ""},
  "Q5": {"resposta": true,  "evidencia": "frases com 13 e 8 palavras; verbo direto 'compara'"},
  "Q6": {"resposta": false, "evidencia": ""},
  "veredito": "reprovado",
  "motivo": "Q2: informação acrescentada"
}
```

## Exemplos de calibração

| Original | Reescrita | Veredito | Motivo |
|---|---|---|---|
| O sistema só aprova a assinatura quando o certificado é válido e não está revogado. | O sistema aprova a assinatura quando o certificado é válido. | reprovado | Q1: remove *só* e *não está revogado* |
| … fora do seu período de validade … | Se o certificado estiver expirado … | reprovado | Q3: *expirado* exclui o certificado ainda não válido |
| … comparação de metodologias estocásticas … sujeitas a alterações regulamentares. | Este estudo compara três algoritmos … regras da competição. | reprovado | Q2: acrescenta *três* e *competição* |
| Deverá ser realizada a reinicialização do serviço após a alteração. | Depois da alteração, reinicie o serviço. | aprovado | Condição temporal preservada; voz ativa |
