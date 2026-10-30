#!/usr/bin/env python3
"""Calibra o judge do PTC-BR contra rótulos humanos (tests/judge/casos.yaml).

Para cada par, monta o prompt com a rubrica + saída do ptc_diff.py, chama `claude -p`
e compara as respostas com o esperado. Mede a concordância por pergunta e a estabilidade
entre execuções.

Uso:
    python3 tests/judge/calibrar.py                       # todos os casos, 1 execução
    python3 tests/judge/calibrar.py --runs 3 --model sonnet
    python3 tests/judge/calibrar.py --caso spec-8.1-escopo --mostrar-prompt
    python3 tests/judge/calibrar.py --sem-diff            # mede o judge sem a checagem determinística

Requer: PyYAML e o Claude Code CLI (`claude`) autenticado. Cada caso custa uma chamada por execução.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]
SKILL = RAIZ / "skills" / "ptc-br"
sys.path.insert(0, str(SKILL / "scripts"))
import ptc_diff  # noqa: E402

PERGUNTAS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
SISTEMA = ("Você é um revisor independente de textos técnicos em português. Aplique a rubrica com rigor. "
           "Procure o que a reescrita perdeu, acrescentou ou mudou de escopo. Responda somente com JSON.")


def montar_prompt(caso: dict, rubrica: str, com_diff: bool) -> str:
    partes = [rubrica, "\n---\n\n# Par a avaliar\n",
              f"regras_alvo: {', '.join(caso.get('regras_alvo', [])) or '—'}\n",
              f"original:\n> {caso['original']}\n",
              f"reescrita:\n> {caso['reescrita']}\n"]
    if caso.get("contexto"):
        partes.append(f"contexto:\n> {caso['contexto']}\n")
    if com_diff:
        diff = ptc_diff.comparar(caso["original"], caso["reescrita"])
        partes.append("diff (ptc_diff.py):\n```json\n" + json.dumps(diff, ensure_ascii=False, indent=2) + "\n```\n")
    partes.append("\nResponda somente com o objeto JSON do formato de saída.")
    return "\n".join(partes)


def chamar_judge(prompt: str, model: str | None, timeout: int) -> dict:
    cmd = ["claude", "-p", "--output-format", "json", "--no-session-persistence",
           "--append-system-prompt", SISTEMA]
    if model:
        cmd += ["--model", model]
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"claude saiu com código {proc.returncode}")
    texto = json.loads(proc.stdout).get("result", "")
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        raise ValueError(f"resposta sem JSON: {texto[:200]}")
    return json.loads(m.group(0))


def resposta(saida: dict, q: str):
    v = saida.get(q)
    return v.get("resposta") if isinstance(v, dict) else v


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--casos", default=str(Path(__file__).with_name("casos.yaml")))
    ap.add_argument("--caso", help="Filtro por id (glob)")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--sem-diff", action="store_true")
    ap.add_argument("--mostrar-prompt", action="store_true", help="Só imprime o prompt do primeiro caso")
    a = ap.parse_args()

    rubrica = (SKILL / "references" / "rubrica-judge.md").read_text(encoding="utf-8")
    casos = yaml.safe_load(Path(a.casos).read_text(encoding="utf-8"))
    if a.caso:
        casos = [c for c in casos if fnmatch.fnmatch(c["id"], a.caso)]
    if not casos:
        print("nenhum caso selecionado", file=sys.stderr)
        return 2
    if a.mostrar_prompt:
        print(montar_prompt(casos[0], rubrica, not a.sem_diff))
        return 0

    acertos, total = defaultdict(int), defaultdict(int)
    instaveis, registros = [], []
    for caso in casos:
        prompt = montar_prompt(caso, rubrica, not a.sem_diff)
        vereditos = []
        for run in range(a.runs):
            try:
                saida = chamar_judge(prompt, a.model, a.timeout)
            except Exception as e:  # noqa: BLE001
                print(f"  {caso['id']} run {run + 1}: ERRO {e}")
                total["erro"] += 1
                continue
            vereditos.append(saida.get("veredito"))
            linha = []
            for chave, esperado in caso["esperado"].items():
                obtido = saida.get("veredito") if chave == "veredito" else resposta(saida, chave)
                ok = obtido == esperado
                acertos[chave] += ok
                total[chave] += 1
                if not ok:
                    linha.append(f"{chave}: esperado {esperado}, obtido {obtido}")
            registros.append({"id": caso["id"], "run": run + 1, "saida": saida, "divergencias": linha})
            marca = "✔" if not linha else "✘"
            print(f"{marca} {caso['id']:<24} run {run + 1}  veredito={saida.get('veredito')}"
                  + (f"  ({'; '.join(linha)})" if linha else ""))
            if linha and saida.get("motivo"):
                print(f"    motivo do judge: {saida['motivo']}")
        if len(set(vereditos)) > 1:
            instaveis.append(caso["id"])

    print("\nConcordância por pergunta:")
    for chave in PERGUNTAS + ["veredito"]:
        if total[chave]:
            print(f"  {chave:<9} {acertos[chave]}/{total[chave]} = {acertos[chave] / total[chave]:.0%}")
    if total["erro"]:
        print(f"  erros de chamada: {total['erro']}")
    if instaveis:
        print(f"Casos instáveis entre execuções: {', '.join(instaveis)}")

    destino = Path(__file__).with_name("resultados")
    destino.mkdir(exist_ok=True)
    arq = destino / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    arq.write_text(json.dumps({"model": a.model, "runs": a.runs, "com_diff": not a.sem_diff,
                               "registros": registros}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetalhes: {arq}")
    return 0 if total["veredito"] and acertos["veredito"] == total["veredito"] else 1


if __name__ == "__main__":
    sys.exit(main())
