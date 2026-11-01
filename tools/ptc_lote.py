#!/usr/bin/env python3
"""PTC-BR — verifica vários arquivos Markdown de uma vez. Usado pela GitHub Action e pelo pre-commit.

Uso:
    python3 tools/ptc_lote.py docs/a.md docs/b.md
    python3 tools/ptc_lote.py --alterados origin/main            # .md alterados em relação a uma referência git
    python3 tools/ptc_lote.py --alterados <sha> --formato github  # anotações para o GitHub Actions

Formatos de saída:
    texto   resumo por arquivo e achados (padrão; usado pelo pre-commit)
    github  anotações ::error/::warning/::notice nas linhas do PR + resumo em $GITHUB_STEP_SUMMARY
    json    lista de resultados por arquivo

Código de saída (--falhar-em, conta só os achados que passaram pelo --min-confianca):
    obrigatoria-alta  (padrão) falha se houver regra obrigatória com confiança alta
    obrigatoria       falha se houver qualquer regra obrigatória
    qualquer          falha se houver qualquer achado
    nunca             nunca falha (só informa)
Só usa a biblioteca padrão.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "ptc-br" / "scripts"))
import ptc_check  # noqa: E402

CONFIANCA = {"baixa": 0, "media": 1, "alta": 2}


def arquivos_alterados(base: str) -> list[str]:
    """Arquivos .md adicionados ou modificados entre `base` e HEAD. Sem base válida, todos os .md do repositório."""
    def git(*args):
        return subprocess.run(["git", *args], capture_output=True, text=True)

    if base and set(base) != {"0"} and git("rev-parse", "--verify", f"{base}^{{commit}}").returncode == 0:
        r = git("diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD", "--", "*.md")
        if r.returncode != 0:   # sem merge-base (clone raso): compara direto
            r = git("diff", "--name-only", "--diff-filter=ACMR", base, "HEAD", "--", "*.md")
    else:
        r = git("ls-files", "*.md")
    return [linha for linha in r.stdout.splitlines() if linha.strip()]


def escapar_dado(s: str) -> str:
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escapar_propriedade(s: str) -> str:
    return escapar_dado(s).replace(":", "%3A").replace(",", "%2C")


def tipo_anotacao(a: dict) -> str:
    """error: obrigatória com confiança alta; notice: confiança baixa (dica de revisão); warning: o resto."""
    if a["nivel"] == "O" and a["confianca"] == "alta":
        return "error"
    if a["confianca"] == "baixa":
        return "notice"
    return "warning"


def anotacao(arquivo: str, a: dict) -> str:
    titulo = f"{a['regra']} ({'obrigatória' if a['nivel'] == 'O' else 'recomendada'}, confiança {a['confianca']})"
    msg = a["mensagem"] + (f" Sugestão: {a['sugestao']}" if a.get("sugestao") else "")
    return (f"::{tipo_anotacao(a)} file={escapar_propriedade(arquivo)},line={a['linha']},"
            f"title={escapar_propriedade(titulo)}::{escapar_dado(msg)}")


def deve_falhar(resultados: list[dict], criterio: str) -> bool:
    achados = [a for r in resultados for a in r["achados"]]
    if criterio == "nunca":
        return False
    if criterio == "qualquer":
        return bool(achados)
    if criterio == "obrigatoria":
        return any(a["nivel"] == "O" for a in achados)
    return any(a["nivel"] == "O" and a["confianca"] == "alta" for a in achados)


def resumo_markdown(resultados: list[dict], criterio: str, falhou: bool) -> str:
    linhas = ["## PTC-BR — verificação de texto técnico", "",
              f"{len(resultados)} arquivo(s) · critério de falha: `{criterio}` · "
              f"resultado: {'**falhou**' if falhou else 'ok'}", "",
              "| Arquivo | Achados | Obrigatórias | Classificação preliminar |", "|---|---|---|---|"]
    for r in resultados:
        s = r["resumo"]
        linhas.append(f"| `{r['arquivo']}` | {len(r['achados'])} | {sum(1 for a in r['achados'] if a['nivel'] == 'O')} "
                      f"| {s['classificacao_preliminar']} |")
    linhas += ["", "As regras de julgamento (J) não são verificadas aqui. Use a skill ptc-br para a revisão completa."]
    return "\n".join(linhas) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verifica vários arquivos Markdown com o PTC-BR.")
    ap.add_argument("arquivos", nargs="*")
    ap.add_argument("--alterados", metavar="REF", help="Verifica os .md alterados entre REF e HEAD")
    ap.add_argument("--ignorar", action="append", default=[], metavar="PADRAO",
                    help="Padrão glob de arquivos a pular (ex.: 'evals/**'). Pode repetir.")
    ap.add_argument("--perfil", default="T", choices=["L", "T", "C", "l", "t", "c"])
    ap.add_argument("--vocabulario", action="append", default=[], metavar="CAMADA")
    ap.add_argument("--siglas", default="")
    ap.add_argument("--min-confianca", default="baixa", choices=list(CONFIANCA))
    ap.add_argument("--falhar-em", default="obrigatoria-alta",
                    choices=["obrigatoria-alta", "obrigatoria", "qualquer", "nunca"])
    ap.add_argument("--formato", default="texto", choices=["texto", "github", "json"])
    a = ap.parse_args(argv)

    arquivos = list(a.arquivos)
    if a.alterados is not None:
        arquivos += arquivos_alterados(a.alterados)
    padroes = [p for x in a.ignorar for p in x.split()]
    arquivos = [f for f in dict.fromkeys(arquivos)
                if f.lower().endswith((".md", ".markdown")) and not any(fnmatch.fnmatch(f, p) for p in padroes)]
    if not arquivos:
        print("PTC-BR: nenhum arquivo Markdown para verificar.")
        return 0

    try:
        vocab, siglas, camadas, ing = None, set(), [], set()
        if a.vocabulario:
            cc = ptc_check.carregar_camadas_completo(a.vocabulario)
            vocab, siglas, camadas, ing = cc["vocabulario"], cc["siglas"], cc["nomes"], cc["ing_aceitos"]
        if a.siglas:
            fonte = Path(a.siglas)
            bruto = fonte.read_text(encoding="utf-8") if fonte.is_file() else a.siglas
            siglas |= {s.strip() for s in bruto.replace(",", "\n").splitlines()
                       if s.strip() and not s.strip().startswith("#")}
    except (OSError, ValueError) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2

    lim = CONFIANCA[a.min_confianca]
    resultados = []
    for arq in arquivos:
        try:
            texto = Path(arq).read_text(encoding="utf-8-sig")
        except OSError as e:
            print(f"erro: {arq}: {e}", file=sys.stderr)
            return 2
        r = ptc_check.verificar(texto, a.perfil, siglas, vocab, camadas, ing_aceitos=ing)
        r["achados"] = [x for x in r["achados"] if CONFIANCA[x["confianca"]] >= lim]
        resultados.append({"arquivo": arq, **r})

    falhou = deve_falhar(resultados, a.falhar_em)
    if a.formato == "json":
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    elif a.formato == "github":
        for r in resultados:
            for x in r["achados"]:
                print(anotacao(r["arquivo"], x))
        resumo = resumo_markdown(resultados, a.falhar_em, falhou)
        destino = os.environ.get("GITHUB_STEP_SUMMARY")
        if destino:
            with open(destino, "a", encoding="utf-8") as f:
                f.write(resumo)
        else:
            print(resumo)
    else:
        total = 0
        for r in resultados:
            if not r["achados"]:
                continue
            print(f"{r['arquivo']}:")
            for x in r["achados"]:
                total += 1
                print(f"  L{x['linha']:<5} {x['regra']} [{x['nivel']}/{x['confianca']}] {x['mensagem']}")
        print(f"PTC-BR: {len(resultados)} arquivo(s), {total} achado(s)"
              + (f" — falhou pelo critério {a.falhar_em}." if falhou else "."))
    return 1 if falhou else 0


if __name__ == "__main__":
    sys.exit(main())
