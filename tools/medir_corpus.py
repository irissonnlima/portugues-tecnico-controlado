#!/usr/bin/env python3
"""Roda o ptc_check.py sobre um corpus de .md e resume os achados por regra e confiança.

Serve para medir ruído (falsos positivos) antes e depois de mudar uma regra ou o léxico.

Uso:
    python3 tools/medir_corpus.py ~/docs/time [outra/pasta ...] [--perfil T] [--exemplos 5] [--regra PTC-17]
    python3 tools/medir_corpus.py ~/docs --json > medicao.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "ptc-br" / "scripts"))
import ptc_check  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pastas", nargs="+")
    ap.add_argument("--perfil", default="T")
    ap.add_argument("--exemplos", type=int, default=0, help="Exemplos por regra")
    ap.add_argument("--regra", help="Mostra exemplos só desta regra")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lematizar", action="store_true", help="Requer simplemma")
    ap.add_argument("--vocabulario", action="append", default=[], help="Camada de vocabulário do time")
    a = ap.parse_args()

    lem = ptc_check.criar_lematizador() if a.lematizar else None
    cc = ptc_check.carregar_camadas_completo(a.vocabulario) if a.vocabulario else None
    vocab, siglas, camadas, ing = (cc["vocabulario"], cc["siglas"], cc["nomes"], cc["ing_aceitos"]) if cc \
        else (None, set(), [], set())
    arquivos = sorted({f for p in a.pastas for f in Path(p).expanduser().rglob("*.md")
                       if "node_modules" not in f.parts and "results" not in f.parts})
    por_regra, por_conf = Counter(), Counter()
    exemplos = defaultdict(list)
    blocos = palavras = 0
    for f in arquivos:
        texto = f.read_text(encoding="utf-8", errors="ignore")
        palavras += len(texto.split())
        r = ptc_check.verificar(texto, a.perfil, siglas, vocab, camadas, lem, ing_aceitos=ing)
        blocos += r["blocos_verificados"]
        for ach in r["achados"]:
            por_regra[ach["regra"]] += 1
            por_conf[(ach["regra"], ach["confianca"])] += 1
            if len(exemplos[ach["regra"]]) < max(a.exemplos, 0):
                exemplos[ach["regra"]].append({"arquivo": str(f), "linha": ach["linha"],
                                               "mensagem": ach["mensagem"], "trecho": ach["trecho"]})

    resumo = {
        "arquivos": len(arquivos), "palavras": palavras, "blocos": blocos,
        "achados": sum(por_regra.values()),
        "por_regra": {k: {"total": v, **{c: por_conf[(k, c)] for c in ("alta", "media", "baixa") if por_conf[(k, c)]}}
                      for k, v in sorted(por_regra.items())},
    }
    if a.json:
        print(json.dumps({**resumo, "exemplos": exemplos}, ensure_ascii=False, indent=2))
        return 0

    print(f"{resumo['arquivos']} arquivos · {palavras} palavras · {blocos} blocos · {resumo['achados']} achados "
          f"({resumo['achados'] / max(palavras, 1) * 1000:.1f} por mil palavras)\n")
    print(f"{'regra':<8} {'total':>6} {'alta':>6} {'media':>6} {'baixa':>6}")
    for k, v in resumo["por_regra"].items():
        print(f"{k:<8} {v['total']:>6} {v.get('alta', 0):>6} {v.get('media', 0):>6} {v.get('baixa', 0):>6}")
    for regra, lista in exemplos.items():
        if a.regra and regra != a.regra:
            continue
        print(f"\n## {regra}")
        for e in lista:
            print(f"  {Path(e['arquivo']).name}:{e['linha']}  {e['mensagem']}\n      › {e['trecho']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
