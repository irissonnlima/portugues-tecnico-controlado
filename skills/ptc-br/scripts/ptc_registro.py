#!/usr/bin/env python3
"""PTC-BR — registro de aceitação dos achados e resumo por regra.

A skill registra, depois de cada revisão, o que a pessoa fez com cada achado: aceito, descartado
(falso positivo ou regra que não se aplica) ou exceção registrada no texto. O resumo mostra a taxa de
aceitação por regra e por verbete. É o dado que indica quais regras funcionam e quais precisam mudar.

O registro fica LOCAL, em um arquivo JSONL. Nada é enviado para fora da máquina.
Caminho padrão: $PTC_REGISTRO, ou $XDG_DATA_HOME/ptc-br/aceitacao.jsonl, ou ~/.local/share/ptc-br/aceitacao.jsonl.

Uso:
    ptc_registro.py registrar --entrada decisoes.json      # lista [{regra, decisao, ...}] ou {"decisoes": [...]}
    ptc_registro.py registrar --regra PTC-25 --decisao descartado --id V-0100 --motivo "termo citado"
    ptc_registro.py resumo [--registro a.jsonl --registro b.jsonl] [--excecoes pasta/] [--json]

Campos de uma decisão: regra (obrigatório), decisao (aceito | descartado | excecao, obrigatório),
id (verbete, ex.: V-0100), confianca, arquivo, motivo. O trecho do texto NÃO é guardado.
Só usa a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

DECISOES = ("aceito", "descartado", "excecao")
CAMPOS = ("regra", "decisao", "id", "confianca", "arquivo", "motivo")
MIN_AMOSTRA = 10          # abaixo disso, a taxa não sustenta conclusão
TAXA_ALERTA = 0.5         # regra com aceitação abaixo disso merece revisão
RE_EXCECAO = re.compile(r"ptc-excecao:\s*(?P<regras>[A-Z0-9,\s-]+?)\s*(?:;|-->)", re.I)


def caminho_padrao() -> Path:
    if os.environ.get("PTC_REGISTRO"):
        return Path(os.environ["PTC_REGISTRO"]).expanduser()
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "ptc-br" / "aceitacao.jsonl"


def versao_spec() -> str:
    try:
        lexico = json.loads(Path(__file__).with_name("lexico.json").read_text(encoding="utf-8"))
        return lexico.get("spec_version", "")
    except (OSError, ValueError):
        return ""


def validar(d: dict) -> dict:
    if not re.fullmatch(r"PTC-\d{2}", str(d.get("regra", ""))):
        raise ValueError(f"regra inválida: {d.get('regra')!r} (use PTC-NN)")
    if d.get("decisao") not in DECISOES:
        raise ValueError(f"decisao inválida: {d.get('decisao')!r} (use {', '.join(DECISOES)})")
    return {k: d[k] for k in CAMPOS if d.get(k)}


def registrar(decisoes: list[dict], destino: Path) -> int:
    linhas = [validar(d) for d in decisoes]
    destino.parent.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    versao = versao_spec()
    with destino.open("a", encoding="utf-8") as f:
        for d in linhas:
            f.write(json.dumps({"data": agora, "spec_version": versao, **d}, ensure_ascii=False) + "\n")
    return len(linhas)


def ler_registros(caminhos: list[Path]) -> list[dict]:
    regs = []
    for c in caminhos:
        if not c.exists():
            continue
        for n, linha in enumerate(c.read_text(encoding="utf-8").splitlines(), 1):
            if linha.strip():
                try:
                    regs.append(json.loads(linha))
                except ValueError:
                    print(f"aviso: {c}:{n}: linha inválida ignorada", file=sys.stderr)
    return regs


def contar_excecoes(pasta: Path) -> Counter:
    """Exceções registradas nos próprios documentos (<!-- ptc-excecao: PTC-03; motivo: ... -->)."""
    c = Counter()
    for f in pasta.rglob("*.md"):
        for m in RE_EXCECAO.finditer(f.read_text(encoding="utf-8", errors="ignore")):
            for r in re.split(r"[,\s]+", m.group("regras").strip()):
                if r:
                    c[r.upper()] += 1
    return c


def resumir(regs: list[dict], excecoes_doc: Counter | None = None) -> dict:
    por_regra: dict[str, Counter] = defaultdict(Counter)
    por_verbete: dict[str, Counter] = defaultdict(Counter)
    motivos: dict[str, Counter] = defaultdict(Counter)
    for r in regs:
        por_regra[r["regra"]][r["decisao"]] += 1
        if r.get("id"):
            por_verbete[r["id"]][r["decisao"]] += 1
        if r["decisao"] == "descartado" and r.get("motivo"):
            motivos[r["regra"]][r["motivo"]] += 1
    for regra, n in (excecoes_doc or {}).items():
        por_regra[regra]["excecao_no_texto"] += n

    def linha(c: Counter) -> dict:
        decididos = c["aceito"] + c["descartado"]
        taxa = c["aceito"] / decididos if decididos else None
        return {"aceito": c["aceito"], "descartado": c["descartado"], "excecao": c["excecao"],
                "excecao_no_texto": c["excecao_no_texto"], "taxa_aceitacao": taxa,
                "amostra_suficiente": decididos >= MIN_AMOSTRA}

    regras = {k: linha(v) for k, v in sorted(por_regra.items())}
    revisar = [k for k, v in regras.items()
               if v["amostra_suficiente"] and v["taxa_aceitacao"] is not None and v["taxa_aceitacao"] < TAXA_ALERTA]
    verbetes = {k: linha(v) for k, v in por_verbete.items()}
    piores = sorted((k for k, v in verbetes.items() if v["descartado"]),
                    key=lambda k: (-verbetes[k]["descartado"], k))[:10]
    return {"registros": len(regs), "por_regra": regras, "regras_a_revisar": revisar,
            "verbetes_mais_descartados": {k: verbetes[k] for k in piores},
            "motivos_de_descarte": {k: dict(v.most_common(5)) for k, v in motivos.items()},
            "criterio": f"revisar regra com taxa de aceitação < {TAXA_ALERTA:.0%} e pelo menos {MIN_AMOSTRA} decisões"}


def imprimir(res: dict) -> None:
    print(f"PTC-BR — registro de aceitação · {res['registros']} decisões\n")
    print(f"{'regra':<8} {'aceito':>7} {'descart.':>9} {'exceção':>8} {'no texto':>9} {'taxa':>6}")
    for k, v in res["por_regra"].items():
        taxa = "—" if v["taxa_aceitacao"] is None else f"{v['taxa_aceitacao']:.0%}"
        if v["taxa_aceitacao"] is not None and not v["amostra_suficiente"]:
            taxa += "*"
        print(f"{k:<8} {v['aceito']:>7} {v['descartado']:>9} {v['excecao']:>8} {v['excecao_no_texto']:>9} {taxa:>6}")
    print(f"\n* amostra pequena (menos de {MIN_AMOSTRA} decisões).")
    if res["regras_a_revisar"]:
        print(f"Regras a revisar: {', '.join(res['regras_a_revisar'])} ({res['criterio']}).")
    if res["verbetes_mais_descartados"]:
        print("Verbetes mais descartados: " + ", ".join(
            f"{k} ×{v['descartado']}" for k, v in res["verbetes_mais_descartados"].items()))
    for regra, m in res["motivos_de_descarte"].items():
        print(f"Motivos de descarte em {regra}: " + "; ".join(f"{x} ×{n}" for x, n in m.items()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Registro de aceitação do PTC-BR.")
    sub = ap.add_subparsers(dest="comando", required=True)
    r = sub.add_parser("registrar", help="Acrescenta decisões ao registro local")
    r.add_argument("--registro", type=Path, default=None)
    r.add_argument("--entrada", type=Path, help="JSON com a lista de decisões")
    for campo in CAMPOS:
        r.add_argument(f"--{campo}")
    s = sub.add_parser("resumo", help="Taxa de aceitação por regra e por verbete")
    s.add_argument("--registro", type=Path, action="append", default=[])
    s.add_argument("--excecoes", type=Path, help="Pasta de .md para contar as exceções registradas no texto")
    s.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    try:
        if a.comando == "registrar":
            destino = a.registro or caminho_padrao()
            if a.entrada:
                dados = json.loads(a.entrada.read_text(encoding="utf-8"))
                decisoes = dados.get("decisoes", []) if isinstance(dados, dict) else dados
            else:
                decisoes = [{k: getattr(a, k) for k in CAMPOS}]
            n = registrar(decisoes, destino)
            print(f"{n} decisão(ões) registrada(s) em {destino}")
            return 0
        caminhos = a.registro or [caminho_padrao()]
        res = resumir(ler_registros(caminhos), contar_excecoes(a.excecoes) if a.excecoes else None)
    except (OSError, ValueError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        imprimir(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
