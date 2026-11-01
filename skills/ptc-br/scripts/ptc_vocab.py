"""PTC-BR — vocabulário controlado: flexão, regex de detecção e camadas de vocabulário do time.

Só usa a biblioteca padrão. Usado pelo ptc_check.py (em tempo de execução) e por
tools/compilar_vocabulario.py (na compilação do vocabulário geral).

Camada de vocabulário do time (JSON ou YAML; YAML exige PyYAML):

    nome: meu-time
    siglas: [DDL, HML]
    sobrepor:                       # muda verbetes do vocabulário geral, por id ou lema
      - id: V-0001                  # verificar
        status: nao_preferido
        preferir: [conferir]
    verbetes:                       # verbetes novos, mesmo schema do vocabulário geral
      - id: T-0001
        lema: subir de versão
        ...

Precedência: a última camada passada vence; qualquer camada vence o vocabulário geral.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

LIMITE = r"[\wÀ-ÿ-]"
STATUS = {"aprovado", "nao_preferido", "proibido", "em_analise"}
CLASSES = {"verbo", "substantivo", "adjetivo", "adverbio", "locucao_verbal", "conectivo", "padrao"}
CAMPOS_SOBREPOR = {"id", "lema", "status", "preferir", "motivo", "regra", "significado_aprovado", "sinonimo_de",
                   "probabilidade", "genero", "dominio"}
RE_ID = re.compile(r"^[A-Z]{1,4}-[0-9]{4}$")


# ---------------------------------------------------------------- flexão

def _radical_subjuntivo(radical: str, terminacao: str) -> str:
    """verifiCar → verifiQUe, cheGar → cheGUe, começar → comeCe, conheCer → conheÇa, eleGer → eleJa."""
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
    """Formas mais frequentes em texto técnico de um verbo regular em -ar, -er ou -ir."""
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
    """Singular e plural de substantivos."""
    for fim, plural in (("ível", "íveis"), ("ável", "áveis"), ("óvel", "óveis"), ("úvel", "úveis")):
        if lema.endswith(fim):
            return [lema, lema[: -len(fim)] + plural]
    if lema.endswith("ão"):
        p = lema[:-2] + "ões"
    elif lema.endswith(("r", "z")):
        p = lema + "es"
    elif lema.endswith(("al", "ol", "ul")):
        p = lema[:-1] + "is"
    elif lema.endswith("el"):
        p = lema[:-2] + "éis"
    elif lema.endswith("il"):
        p = lema[:-1] + "s"
    elif lema.endswith("m"):
        p = lema[:-1] + "ns"
    elif lema.endswith("s"):
        p = lema
    else:
        p = lema + "s"
    return sorted({lema, p})


def flexionar_adjetivo(lema: str) -> list[str]:
    """Gênero e número: supracitado → supracitada, supracitados, supracitadas."""
    if lema.endswith("o"):
        r = lema[:-1]
        return [r + "o", r + "a", r + "os", r + "as"]
    return flexionar_nome(lema)


def formas_do_verbete(v: dict) -> list[str]:
    if v.get("formas"):
        return list(v["formas"])
    lema, classe = v["lema"], v.get("classe")
    if v.get("flexao") == "nenhuma" or classe in ("conectivo", "padrao", "adverbio"):
        return [lema]
    if classe == "verbo":
        return flexionar_verbo(lema)
    if classe == "locucao_verbal":
        verbo, _, resto = lema.partition(" ")
        return [f"{f} {resto}".strip() for f in flexionar_verbo(verbo)]
    if classe == "adjetivo":
        return flexionar_adjetivo(lema)
    return flexionar_nome(lema)


def regex_do_verbete(v: dict) -> str:
    if v.get("padrao"):
        return v["padrao"]
    formas = sorted(set(formas_do_verbete(v)), key=lambda f: (-len(f), f))
    alt = "|".join(re.escape(f).replace(r"\ ", r"\s+") for f in formas)
    return rf"(?<!{LIMITE})(?:{alt})(?!{LIMITE})"


def lematizavel(v: dict) -> bool:
    """O verbete pode ser achado por lema? Não quando o autor fixou as formas (ambiguidade) ou usou padrão."""
    return (not v.get("padrao") and not v.get("formas") and v.get("flexao") != "nenhuma"
            and v.get("classe") in ("verbo", "substantivo", "adjetivo") and " " not in v["lema"]
            and "-" not in v["lema"])


# ---------------------------------------------------------------- validação mínima (sem jsonschema)

def validar_verbete(v: dict) -> list[str]:
    erros, vid = [], v.get("id", "?")
    for campo in ("id", "lema", "classe", "status", "significado_aprovado"):
        if not v.get(campo):
            erros.append(f"{vid}: campo obrigatório ausente: {campo}")
    if v.get("id") and not RE_ID.match(v["id"]):
        erros.append(f"{vid}: id deve ter o formato PREFIXO-NNNN (ex.: V-0001, T-0001)")
    if v.get("status") and v["status"] not in STATUS:
        erros.append(f"{vid}: status inválido: {v['status']}")
    if v.get("classe") and v["classe"] not in CLASSES:
        erros.append(f"{vid}: classe inválida: {v['classe']}")
    if v.get("status") in ("nao_preferido", "proibido", "em_analise") and not v.get("preferir"):
        erros.append(f"{vid}: status {v['status']} exige 'preferir'")
    try:
        re.compile(regex_do_verbete(v), re.I)
    except (re.error, KeyError) as e:
        erros.append(f"{vid}: regex inválida: {e}")
    return erros


# ---------------------------------------------------------------- camadas

def _ler(caminho: Path):
    texto = caminho.read_text(encoding="utf-8")
    if caminho.suffix.lower() == ".json":
        return json.loads(texto)
    try:
        import yaml
    except ImportError as e:
        raise ValueError(f"{caminho}: camada em YAML exige PyYAML (pip install pyyaml) ou use .json") from e
    return yaml.safe_load(texto)


def carregar_camada(caminho: str | Path) -> dict:
    caminho = Path(caminho)
    dados = _ler(caminho) or {}
    if not isinstance(dados, dict):
        raise ValueError(f"{caminho}: a camada deve ser um objeto com 'sobrepor', 'verbetes' e/ou 'siglas'")
    desconhecidas = set(dados) - {"nome", "descricao", "siglas", "sobrepor", "verbetes"}
    if desconhecidas:
        raise ValueError(f"{caminho}: chaves desconhecidas: {sorted(desconhecidas)}")
    dados.setdefault("nome", caminho.stem)
    return dados


def aplicar_camada(base: list[dict], camada: dict) -> tuple[list[dict], set[str]]:
    """Devolve (verbetes resultantes, siglas da camada). Não altera `base`."""
    resultado = [dict(v) for v in base]
    por_id = {v["id"]: v for v in resultado}
    por_lema = {v["lema"].lower(): v for v in resultado}
    erros = []
    nome = camada.get("nome", "camada")

    for s in camada.get("sobrepor") or []:
        extras = set(s) - CAMPOS_SOBREPOR
        if extras:
            erros.append(f"{nome}: sobrepor {s.get('id') or s.get('lema')}: campos não permitidos {sorted(extras)}")
            continue
        alvo = por_id.get(s.get("id", "")) or por_lema.get(str(s.get("lema", "")).lower())
        if not alvo:
            erros.append(f"{nome}: sobrepor: verbete não encontrado: {s.get('id') or s.get('lema')}")
            continue
        for k, x in s.items():
            if k not in ("id", "lema"):
                alvo[k] = x
        alvo["camada"] = nome
        if alvo.get("status") == "aprovado" and "preferir" not in s:
            alvo.pop("preferir", None)
        erros += [f"{nome}: {e}" for e in validar_verbete(alvo)]

    for v in camada.get("verbetes") or []:
        v = dict(v)
        if v.get("id") in por_id:
            erros.append(f"{nome}: verbete {v['id']} já existe; use 'sobrepor' para alterar")
            continue
        erros += [f"{nome}: {e}" for e in validar_verbete(v)]
        v.setdefault("regra", "PTC-25")
        v["regex"] = regex_do_verbete(v)
        v["lematizavel"] = lematizavel(v)
        v["camada"] = nome
        resultado.append(v)
        por_id[v["id"]] = v

    if erros:
        raise ValueError("Camada de vocabulário inválida:\n  " + "\n  ".join(erros))
    siglas = {str(x).strip() for x in (camada.get("siglas") or []) if str(x).strip()}
    return resultado, siglas
