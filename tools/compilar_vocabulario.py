#!/usr/bin/env python3
"""Compila o vocabulário controlado (YAML) para o JSON que o ptc_check.py usa.

- Valida cada verbete contra references/vocabulario/schema.json (com jsonschema, se instalado)
  e com checagens próprias: IDs únicos, preferir obrigatório, regex válida.
- Gera as formas flexionadas a partir do lema (verbos regulares em -ar/-er/-ir, plural de substantivos).
- Escreve skills/ptc-br/scripts/vocabulario.json com uma regex de detecção por verbete.

Uso:
    python3 tools/compilar_vocabulario.py            # compila
    python3 tools/compilar_vocabulario.py --checar   # só confere se o JSON está atualizado (para CI)

Requer PyYAML (só para quem edita o vocabulário; os scripts da skill não precisam).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
SKILL = RAIZ / "skills" / "ptc-br"
FONTES = sorted((SKILL / "references" / "vocabulario").glob("*.yaml"))
SCHEMA = SKILL / "references" / "vocabulario" / "schema.json"
SAIDA = SKILL / "scripts" / "vocabulario.json"
SPEC_VERSION = "0.2.0"

LIMITE = r"[\wÀ-ÿ-]"


# ---------------------------------------------------------------- flexão

def _radical_subjuntivo(radical: str, terminacao: str) -> str:
    """Ajustes ortográficos: verifiCar → verifiQUe, cheGar → cheGUe, começar → comeCe, conheCer → conheÇa."""
    if terminacao == "ar":
        if radical.endswith("c"):
            return radical[:-1] + "qu"
        if radical.endswith("g"):
            return radical + "u"
        if radical.endswith("ç"):
            return radical[:-1] + "c"
    if terminacao == "er":
        if radical.endswith("c"):
            return radical[:-1] + "ç"
        if radical.endswith("g"):
            return radical[:-1] + "j"
    return radical


def flexionar_verbo(lema: str) -> list[str]:
    radical, term = lema[:-2], lema[-2:]
    if term not in ("ar", "er", "ir"):
        return [lema]
    sub = _radical_subjuntivo(radical, term)
    if term == "ar":
        formas = ["ar", "a", "am", "ou", "aram", "ado", "ada", "ados", "adas", "ando", "ará", "arão", "ava", "avam",
                  "asse", "assem", "ar-se", "a-se", "am-se"]
        subj = ["e", "em", "e-se"]
    elif term == "er":
        formas = ["er", "e", "em", "eu", "eram", "ido", "ida", "idos", "idas", "endo", "erá", "erão", "ia", "iam"]
        subj = ["a", "am"]
    else:
        formas = ["ir", "e", "em", "iu", "iram", "ido", "ida", "idos", "idas", "indo", "irá", "irão", "ia", "iam"]
        subj = ["a", "am"]
    return [radical + f for f in formas] + [sub + f for f in subj]


def flexionar_nome(lema: str) -> list[str]:
    if lema.endswith("ão"):
        plural = lema[:-2] + "ões"
    elif lema.endswith(("r", "z")):
        plural = lema + "es"
    elif lema.endswith("al") or lema.endswith("ol") or lema.endswith("ul"):
        plural = lema[:-1] + "is"
    elif lema.endswith("el"):
        plural = lema[:-2] + "éis"
    elif lema.endswith("il"):
        plural = lema[:-1] + "s"
    elif lema.endswith("m"):
        plural = lema[:-1] + "ns"
    elif lema.endswith("s"):
        plural = lema
    else:
        plural = lema + "s"
    return sorted({lema, plural})


def formas_do_verbete(v: dict) -> list[str]:
    if v.get("formas"):
        return v["formas"]
    lema = v["lema"]
    if v.get("flexao") == "nenhuma" or v["classe"] in ("conectivo", "padrao"):
        return [lema]
    if v["classe"] == "verbo":
        return flexionar_verbo(lema)
    if v["classe"] == "locucao_verbal":
        verbo, _, resto = lema.partition(" ")
        return [f"{f} {resto}".strip() for f in flexionar_verbo(verbo)]
    return flexionar_nome(lema)


def regex_do_verbete(v: dict) -> str:
    if v.get("padrao"):
        return v["padrao"]
    formas = sorted(set(formas_do_verbete(v)), key=lambda f: (-len(f), f))
    alt = "|".join(re.escape(f).replace(r"\ ", r"\s+") for f in formas)
    return rf"(?<!{LIMITE})(?:{alt})(?!{LIMITE})"


# ---------------------------------------------------------------- validação

def validar(verbetes: list[dict]) -> list[str]:
    erros = []
    try:
        import jsonschema
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        val = jsonschema.Draft202012Validator(schema)
        for v in verbetes:
            for e in val.iter_errors(v):
                erros.append(f"{v.get('id', '?')}: {e.message}")
    except ImportError:
        print("aviso: jsonschema não instalado; só as checagens próprias rodam.", file=sys.stderr)

    vistos = {}
    for v in verbetes:
        vid = v.get("id")
        if vid in vistos:
            erros.append(f"{vid}: ID duplicado (também em '{vistos[vid]}')")
        vistos[vid] = v.get("lema")
        if v.get("status") in ("nao_preferido", "proibido", "em_analise") and not v.get("preferir"):
            erros.append(f"{vid}: status {v['status']} exige 'preferir'")
        if v.get("status") == "aprovado" and v.get("padrao"):
            erros.append(f"{vid}: verbete aprovado não deve ter 'padrao' (padrões só servem para detectar)")
        try:
            re.compile(regex_do_verbete(v), re.I)
        except re.error as e:
            erros.append(f"{vid}: regex inválida: {e}")
    return erros


def compilar() -> dict:
    verbetes = []
    for fonte in FONTES:
        dados = yaml.safe_load(fonte.read_text(encoding="utf-8")) or []
        for v in dados:
            v["_fonte"] = fonte.name
        verbetes += dados
    erros = validar([{k: x for k, x in v.items() if k != "_fonte"} for v in verbetes])
    if erros:
        raise SystemExit("Vocabulário inválido:\n  " + "\n  ".join(erros))

    saida = []
    for v in sorted(verbetes, key=lambda x: x["id"]):
        item = {k: v[k] for k in ("id", "lema", "classe", "status", "significado_aprovado") if k in v}
        for k in ("preferir", "preferida_em_instrucoes", "sentidos", "motivo", "exemplo_correto", "exemplo_incorreto"):
            if k in v:
                item[k] = v[k]
        item["regra"] = v.get("regra", "PTC-25")
        item["fonte"] = v["_fonte"]
        item["regex"] = regex_do_verbete(v)
        saida.append(item)
    return {
        "spec_version": SPEC_VERSION,
        "aviso": "Arquivo gerado por tools/compilar_vocabulario.py. Edite os .yaml em references/vocabulario/.",
        "total": len(saida),
        "verbetes": saida,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--checar", action="store_true", help="Falha se o JSON gerado estiver desatualizado")
    a = ap.parse_args()
    novo = json.dumps(compilar(), ensure_ascii=False, indent=1) + "\n"
    if a.checar:
        atual = SAIDA.read_text(encoding="utf-8") if SAIDA.exists() else ""
        if atual != novo:
            print("vocabulario.json desatualizado: rode python3 tools/compilar_vocabulario.py", file=sys.stderr)
            return 1
        print("vocabulario.json atualizado")
        return 0
    SAIDA.write_text(novo, encoding="utf-8")
    dados = json.loads(novo)
    por_status = {}
    for v in dados["verbetes"]:
        chave = "polissemico" if v.get("sentidos") else v["status"]
        por_status[chave] = por_status.get(chave, 0) + 1
    print(f"{dados['total']} verbetes → {SAIDA.relative_to(RAIZ)}  {por_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
