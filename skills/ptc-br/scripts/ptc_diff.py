#!/usr/bin/env python3
"""PTC-BR — checagem determinística de preservação de sentido (PTC-22).

Compara um trecho original com a reescrita e aponta perda ou adição de:
números, negações, restrições, condições, alternativas ("ou"), comparadores e modais.
Também lista termos novos que não têm raiz no original, para o judge conferir.

Uso:
    python3 ptc_diff.py --original "texto" --reescrita "texto" [--json]
    python3 ptc_diff.py --original-arquivo a.txt --reescrita-arquivo b.txt [--json]
    python3 ptc_diff.py --pares pares.jsonl [--json]     # uma linha JSON por par: {"original": ..., "reescrita": ...}

Código de saída: 0 = nenhum alerta de severidade alta; 1 = há alerta alto; 2 = erro.
Este script não decide sozinho: ele reduz o trabalho do judge (references/rubrica-judge.md).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

LEXICO = json.loads((Path(__file__).with_name("lexico.json")).read_text(encoding="utf-8"))
UNIDADES = set(LEXICO["unidades"])

NUM_PALAVRAS = {
    "dois": 2, "duas": 2, "três": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9,
    "dez": 10, "onze": 11, "doze": 12, "quinze": 15, "vinte": 20, "trinta": 30, "cem": 100, "cento": 100,
    "mil": 1000, "metade": 0.5, "dobro": 2, "triplo": 3, "dezena": 10, "dezenas": 10, "centena": 100,
    "centenas": 100, "primeiro": 1, "primeira": 1, "terceiro": 3, "terceira": 3,
}

# Classes semânticas. Cada classe soma ocorrências de qualquer termo dela (sinônimos se compensam).
CLASSES = {
    "negacao": LEXICO["negacoes"],
    "restricao": ["só", "somente", "apenas", "unicamente", "exclusivamente", "exceto", "salvo", "senão",
                  "a menos que", "nunca mais"],
    "condicao": ["se", "caso", "quando", "desde que", "contanto que", "a menos que", "enquanto", "sempre que"],
    "alternativa": ["ou", "e/ou", "seja"],
    "comparador": ["maior", "menor", "acima", "abaixo", "superior", "inferior", "mínimo", "máximo", "pelo menos",
                   "no mínimo", "no máximo", "até", "entre", "mais de", "menos de", "igual", ">", "<", "≥", "≤",
                   ">=", "<=", "="],
    "obrigacao": ["deve", "devem", "deverá", "deverão", "precisa", "precisam", "obrigatório", "obrigatória",
                  "obrigatoriamente", "necessário", "necessária", "exige", "exigido"],
    "permissao": ["pode", "podem", "poderá", "poderão", "opcional", "opcionalmente", "permitido", "permitida",
                  "facultativo"],
    "proibicao": ["proibido", "proibida", "vedado", "vedada", "não deve", "não pode", "nunca"],
}
# Severidade quando a classe DIMINUI / AUMENTA na reescrita.
SEVERIDADE = {
    "negacao": ("alta", "media"),
    "restricao": ("alta", "media"),
    "condicao": ("media", "baixa"),
    "alternativa": ("alta", "media"),
    "comparador": ("alta", "media"),
    "obrigacao": ("baixa", "baixa"),   # imperativo substitui "deve" de forma legítima
    "permissao": ("media", "media"),
    "proibicao": ("alta", "alta"),
}
SIMBOLOS = {">", "<", "≥", "≤", ">=", "<=", "="}

STOP = set("""a o as os um uma uns umas de do da dos das no na nos nas em por para com sem que se e ou
ao aos à às pelo pela pelos pelas este esta isto esse essa isso aquele aquela seu sua seus suas
é são foi ser está estão estar ter tem têm como mais também depois antes então quando onde""".split())


def normalizar(t: str) -> str:
    return re.sub(r"\s+", " ", t.lower()).strip()


def sem_acento(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def contar_termo(termo: str, texto: str) -> int:
    if termo in SIMBOLOS:
        return len(re.findall(rf"(?<![<>=≥≤]){re.escape(termo)}(?![<>=≥≤])", texto))
    return len(re.findall(rf"(?<![\wÀ-ÿ/-]){re.escape(termo)}(?![\wÀ-ÿ/-])", texto))


def contar_classe(classe: str, texto: str) -> int:
    termos = sorted(CLASSES[classe], key=len, reverse=True)
    t, total = texto, 0
    for termo in termos:   # termos longos primeiro, e retirados do texto para não contar duas vezes
        n = contar_termo(termo, t)
        if n:
            total += n
            t = re.sub(rf"(?<![\wÀ-ÿ/-]){re.escape(termo)}(?![\wÀ-ÿ/-])", " ", t) if termo not in SIMBOLOS else t.replace(termo, " ")
    return total


def numeros(texto: str) -> Counter:
    achados = Counter()
    toks = texto.split()
    for i, tok in enumerate(toks):
        limpo = tok.strip(".,;:!?()[]\"'“”")
        m = re.fullmatch(r"([+-]?\d+(?:[.,]\d+)*)(%|[A-Za-zµΩ°²³]+)?", limpo)
        if m:
            valor = m.group(1).replace(".", "").replace(",", ".") if re.search(r",\d", m.group(1)) else m.group(1)
            unidade = m.group(2) or ""
            if not unidade and i + 1 < len(toks) and toks[i + 1].strip(".,;:") in UNIDADES:
                unidade = toks[i + 1].strip(".,;:")
            achados[f"{valor}{(' ' + unidade) if unidade else ''}"] += 1
        elif limpo.lower() in NUM_PALAVRAS:
            achados[f"{limpo.lower()} (={NUM_PALAVRAS[limpo.lower()]:g})"] += 1
    return achados


def raizes(texto: str) -> dict[str, str]:
    saida = {}
    for p in re.findall(r"[\wÀ-ÿ]+", texto.lower()):
        if len(p) >= 5 and p not in STOP and not p.isdigit():
            saida.setdefault(sem_acento(p)[:5], p)
    return saida


def comparar(original: str, reescrita: str) -> dict:
    o, r = normalizar(original), normalizar(reescrita)
    alertas = []

    no, nr = numeros(original), numeros(reescrita)
    perdidos, novos = no - nr, nr - no
    if perdidos:
        alertas.append({"classe": "numero", "severidade": "alta", "tipo": "perda",
                        "detalhe": f"Números do original ausentes na reescrita: {sorted(perdidos.elements())}"})
    if novos:
        alertas.append({"classe": "numero", "severidade": "alta", "tipo": "adicao",
                        "detalhe": f"Números novos na reescrita: {sorted(novos.elements())}"})

    for classe in CLASSES:
        co, cr = contar_classe(classe, o), contar_classe(classe, r)
        if cr < co:
            alertas.append({"classe": classe, "severidade": SEVERIDADE[classe][0], "tipo": "perda",
                            "detalhe": f"{classe}: {co} no original, {cr} na reescrita"})
        elif cr > co:
            alertas.append({"classe": classe, "severidade": SEVERIDADE[classe][1], "tipo": "adicao",
                            "detalhe": f"{classe}: {co} no original, {cr} na reescrita"})

    ro, rr = raizes(original), raizes(reescrita)
    termos_novos = sorted(rr[k] for k in rr.keys() - ro.keys())
    termos_ausentes = sorted(ro[k] for k in ro.keys() - rr.keys())

    altas = sum(1 for a in alertas if a["severidade"] == "alta")
    return {
        "alertas": alertas,
        "termos_novos": termos_novos,
        "termos_ausentes": termos_ausentes,
        "resumo": {"alertas": len(alertas), "altos": altas,
                   "veredito_preliminar": "revisar" if altas else "sem perda detectada"},
        "observacao": "Termos novos/ausentes são informativos: o judge decide se mudam o sentido.",
    }


def imprimir(res: dict, titulo: str = "") -> None:
    if titulo:
        print(f"== {titulo}")
    print(f"Alertas: {res['resumo']['alertas']} (altos: {res['resumo']['altos']}) · {res['resumo']['veredito_preliminar']}")
    for a in res["alertas"]:
        print(f"  [{a['severidade']}] {a['tipo']:<7} {a['detalhe']}")
    if res["termos_novos"]:
        print(f"  termos novos: {', '.join(res['termos_novos'])}")
    if res["termos_ausentes"]:
        print(f"  termos ausentes: {', '.join(res['termos_ausentes'])}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Checagem de preservação de sentido PTC-BR (PTC-22).")
    ap.add_argument("--original")
    ap.add_argument("--reescrita")
    ap.add_argument("--original-arquivo")
    ap.add_argument("--reescrita-arquivo")
    ap.add_argument("--pares", help="Arquivo JSONL com {original, reescrita} por linha")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        if a.pares:
            linhas = [json.loads(l) for l in Path(a.pares).read_text(encoding="utf-8").splitlines() if l.strip()]
            resultados = [{"id": p.get("id", i), **comparar(p["original"], p["reescrita"])} for i, p in enumerate(linhas)]
            if a.json:
                print(json.dumps(resultados, ensure_ascii=False, indent=2))
            else:
                for res in resultados:
                    imprimir(res, str(res["id"]))
            return 1 if any(r["resumo"]["altos"] for r in resultados) else 0

        orig = a.original if a.original is not None else Path(a.original_arquivo).read_text(encoding="utf-8-sig")
        reesc = a.reescrita if a.reescrita is not None else Path(a.reescrita_arquivo).read_text(encoding="utf-8-sig")
    except (OSError, TypeError, KeyError, json.JSONDecodeError) as e:
        print(f"erro: {e}. Informe --original/--reescrita, os arquivos ou --pares.", file=sys.stderr)
        return 2

    res = comparar(orig, reesc)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        imprimir(res)
    return 1 if res["resumo"]["altos"] else 0


if __name__ == "__main__":
    sys.exit(main())
