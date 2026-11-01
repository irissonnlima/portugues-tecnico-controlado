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
FONTES = sorted((SKILL / "references" / "vocabulario").glob("*.yaml")) + \
    sorted((SKILL / "references" / "glossarios").glob("*.yaml"))
SCHEMA = SKILL / "references" / "vocabulario" / "schema.json"
SAIDA = SKILL / "scripts" / "vocabulario.json"
SPEC_VERSION = "0.5.1"

sys.path.insert(0, str(SKILL / "scripts"))
from ptc_vocab import (flexionar_adjetivo, flexionar_nome, flexionar_verbo,  # noqa: E402,F401
                       formas_do_verbete, lematizavel, regex_do_verbete, validar_verbete)


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
        erros += [e for e in validar_verbete(v) if e not in erros]
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
        try:
            dados = yaml.safe_load(fonte.read_text(encoding="utf-8")) or []
        except yaml.YAMLError as e:
            raise SystemExit(f"YAML inválido em {fonte.name}: {e}") from None
        for v in dados:
            v["_fonte"] = fonte.name
        verbetes += dados
    erros = validar([{k: x for k, x in v.items() if k != "_fonte"} for v in verbetes])
    if erros:
        raise SystemExit("Vocabulário inválido:\n  " + "\n  ".join(erros))

    saida = []
    for v in sorted(verbetes, key=lambda x: x["id"]):
        item = {k: v[k] for k in ("id", "lema", "classe", "status", "significado_aprovado") if k in v}
        for k in ("preferir", "preferida_em_instrucoes", "sinonimo_de", "probabilidade", "dominio", "genero", "sentidos", "motivo", "exemplo_correto",
                  "exemplo_incorreto"):
            if k in v:
                item[k] = v[k]
        item["regra"] = v.get("regra", "PTC-25")
        item["fonte"] = v["_fonte"]
        item["regex"] = regex_do_verbete(v)
        item["lematizavel"] = lematizavel(v)
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
