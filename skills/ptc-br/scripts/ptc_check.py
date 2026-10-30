#!/usr/bin/env python3
"""PTC-BR — verificador determinístico de regras automáticas (A) e parciais (P).

Uso:
    python3 ptc_check.py ARQUIVO.md [--perfil L|T|C] [--json] [--min-confianca baixa|media|alta]
    python3 ptc_check.py --texto "Frase a verificar." [--json]
    cat arquivo.md | python3 ptc_check.py -

Só usa a biblioteca padrão. As regras de contagem seguem a seção 5 de references/regras.md.

Saída: lista de achados com regra, nível no perfil (O/R), confiança, linha, trecho e sugestão.
Código de saída: 0 = nenhuma obrigatória com confiança alta; 1 = há obrigatória com confiança alta; 2 = erro.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

SPEC_VERSION = "0.1.1"
LEXICO = json.loads((Path(__file__).with_name("lexico.json")).read_text(encoding="utf-8"))

# Nível de cada regra por perfil (seção 3.1 da spec). Ausente = não se aplica.
MATRIZ = {
    "L": {"PTC-03": "R", "PTC-05": "R", "PTC-11": "R", "PTC-12": "R", "PTC-17": "R", "PTC-18": "R",
          "PTC-21": "O", "PTC-23": "R"},
    "T": {"PTC-03": "O", "PTC-04": "R", "PTC-05": "O", "PTC-11": "R", "PTC-12": "R", "PTC-15": "R",
          "PTC-17": "O", "PTC-18": "O", "PTC-21": "O", "PTC-23": "R", "PTC-24": "O"},
    "C": {"PTC-03": "O", "PTC-04": "O", "PTC-05": "O", "PTC-11": "O", "PTC-12": "O", "PTC-15": "O",
          "PTC-17": "O", "PTC-18": "O", "PTC-21": "O", "PTC-23": "O", "PTC-24": "O"},
}
CONFIANCA = {"baixa": 0, "media": 1, "alta": 2}

CODE_TOKEN = "⟦código⟧"
URL_TOKEN = "⟦url⟧"
PROTECT = "§"


@dataclass
class Bloco:
    tipo: str            # paragrafo | item_numerado | item | citacao
    linha: int
    texto: str
    excecoes: dict = field(default_factory=dict)   # regra -> motivo


@dataclass
class Achado:
    regra: str
    nivel: str
    confianca: str
    linha: int
    trecho: str
    mensagem: str
    sugestao: str = ""


# ---------------------------------------------------------------- leitura do markdown

RE_LISTA = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
RE_EXCECAO = re.compile(r"ptc-excecao:\s*(?P<regras>[A-Z0-9,\s-]+?)\s*(?:;\s*motivo:\s*(?P<motivo>.*?))?\s*-->", re.I)
RE_SIGLAS_DECL = re.compile(r"ptc-siglas:\s*(?P<lista>.*?)\s*-->", re.I)


def ler_blocos(texto: str) -> tuple[list[Bloco], set[str], list[Achado]]:
    """Divide o markdown em blocos verificáveis. Ignora código, tabelas, títulos e front matter."""
    linhas = texto.splitlines()
    blocos: list[Bloco] = []
    siglas_decl: set[str] = set()
    achados: list[Achado] = []
    atual: Bloco | None = None
    excecao_pendente: dict = {}
    em_codigo = False
    em_comentario = ""
    i = 0

    def fechar():
        nonlocal atual
        if atual and atual.texto.strip():
            blocos.append(atual)
        atual = None

    # front matter YAML
    if linhas and linhas[0].strip() == "---":
        for j in range(1, len(linhas)):
            if linhas[j].strip() == "---":
                i = j + 1
                break

    while i < len(linhas):
        n, linha = i + 1, linhas[i]
        i += 1
        s = linha.strip()

        if em_comentario:
            em_comentario += " " + s
            if "-->" in s:
                s, em_comentario = em_comentario, ""
            else:
                continue
        elif s.startswith("<!--") and "-->" not in s:
            em_comentario = s
            continue

        if s.startswith(("```", "~~~")):
            em_codigo = not em_codigo
            fechar()
            continue
        if em_codigo:
            continue

        if s.startswith("<!--"):
            fechar()
            m = RE_EXCECAO.search(s)
            if m:
                motivo = (m.group("motivo") or "").strip()
                for r in re.split(r"[,\s]+", m.group("regras").strip()):
                    if r:
                        excecao_pendente[r.upper()] = motivo
                if not motivo:
                    achados.append(Achado("PTC-24", "", "alta", n, s,
                                          "Exceção registrada sem motivo.",
                                          "Use: <!-- ptc-excecao: PTC-NN; motivo: ... -->"))
            m = RE_SIGLAS_DECL.search(s)
            if m:
                siglas_decl.update(x.strip() for x in m.group("lista").split(",") if x.strip())
            continue

        if not s:
            fechar()
            continue
        if s.startswith("#") or s.startswith("|") or re.fullmatch(r"[-*_ ]{3,}", s):
            fechar()
            continue

        m = RE_LISTA.match(linha)
        if m:
            fechar()
            tipo = "item_numerado" if m.group(2)[0].isdigit() else "item"
            atual = Bloco(tipo, n, m.group(3), excecao_pendente)
            excecao_pendente = {}
            continue

        if s.startswith(">"):
            conteudo = s.lstrip(">").strip()
            if atual and atual.tipo == "citacao":
                atual.texto += " " + conteudo
            else:
                fechar()
                atual = Bloco("citacao", n, conteudo, excecao_pendente)
                excecao_pendente = {}
            continue

        if atual and (atual.tipo in ("paragrafo",) or linha.startswith((" ", "\t"))):
            atual.texto += " " + s
        else:
            fechar()
            atual = Bloco("paragrafo", n, s, excecao_pendente)
            excecao_pendente = {}
    fechar()
    return blocos, siglas_decl, achados


def limpar_inline(texto: str) -> str:
    """Remove marcação markdown e troca código e URLs por um token único."""
    t = re.sub(r"`[^`]+`", f" {CODE_TOKEN} ", texto)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"https?://\S+", URL_TOKEN, t)
    t = re.sub(r"\[!(WARNING|IMPORTANT|CAUTION|NOTE|TIP)\]", lambda m: {
        "WARNING": "Aviso:", "IMPORTANT": "Importante:", "CAUTION": "Cuidado:", "NOTE": "Nota:", "TIP": "Nota:"}[m.group(1)], t)
    t = re.sub(r"(\*\*|__|\*|_)(\S(?:.*?\S)?)\1", r"\2", t)
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------- frases e palavras

def _re_abreviacoes() -> re.Pattern:
    abrevs = sorted(LEXICO["abreviacoes"], key=len, reverse=True)
    alt = "|".join(re.escape(a).replace(r"\ ", r"\s?") for a in abrevs)
    return re.compile(rf"(?<![\w])({alt})\.", re.I)


RE_ABREV = _re_abreviacoes()


def dividir_frases(texto: str) -> list[str]:
    t = RE_ABREV.sub(lambda m: m.group(1).replace(".", PROTECT) + PROTECT, texto)
    t = re.sub(r"(\d)\.(?=\d)", rf"\1{PROTECT}", t)
    t = re.sub(r"\b(v?\d+)\.(?=\d)", rf"\1{PROTECT}", t)
    partes = re.split(r"(?<=[.!?])[\"”')\]]?\s+(?=\S)", t)
    return [p.replace(PROTECT, ".").strip() for p in partes if p.strip()]


RE_NUMERO = re.compile(r"^[+-]?\d[\d.,]*$")
RE_ID_NORMA = re.compile(r"^(?:[A-Z]{2,}|[\w./:-]*\d[\w./:-]*)$")
UNIDADES = set(LEXICO["unidades"])


def contar_palavras(frase: str) -> int:
    brutos = frase.split()
    toks = []
    for b in brutos:
        if b in (CODE_TOKEN, URL_TOKEN):
            toks.append(b)
            continue
        limpo = b.strip(".,;:!?()[]{}\"'“”‘’«»")
        if limpo and re.search(r"\w", limpo):
            toks.append(limpo)
    total, k = 0, 0
    while k < len(toks):
        tok = toks[k]
        # número + unidade = 1
        if RE_NUMERO.match(tok) and k + 1 < len(toks) and toks[k + 1] in UNIDADES:
            total, k = total + 1, k + 2
            continue
        # identificador de norma (ABNT NBR ISO 24495-1) = 1
        if re.fullmatch(r"[A-Z]{2,}", tok):
            j = k
            while j < len(toks) and RE_ID_NORMA.match(toks[j]) and (re.fullmatch(r"[A-Z]{2,}", toks[j]) or re.search(r"\d", toks[j])):
                j += 1
            run = toks[k:j]
            if len(run) >= 2 and any(re.search(r"\d", x) for x in run):
                total, k = total + 1, j
                continue
        total, k = total + 1, k + 1
    return total


def palavras(texto: str) -> list[str]:
    return re.findall(r"[\wÀ-ÿ]+(?:-[\wÀ-ÿ]+)*", texto.lower())


def resumo(frase: str, n: int = 90) -> str:
    return frase if len(frase) <= n else frase[: n - 1] + "…"


# ---------------------------------------------------------------- regras

def _ocorre(termo: str, texto: str) -> re.Match | None:
    return re.search(rf"(?<![\wÀ-ÿ]){re.escape(termo)}(?![\wÀ-ÿ])", texto, re.I)


ARTIGOS = r"(?:a|o|à|ao|as|os|às|aos|uma|um|umas|uns|esta|este|essa|esse|nova|novo)"
SUPORTE_FRACO = {"executar", "executa", "execute", "executam", "fazer", "faz", "faça", "fazem", "fez", "feito", "feita",
                 "faz-se", "dar", "dá", "dê", "dão", "deu", "levar", "leva", "leve", "levam"}
RE_NOMINAL = re.compile(r"(ção|ções|mento|mentos|agem|agens)$")


def regra_nominalizacao(frase: str) -> list[tuple[str, str]]:
    """PTC-11: verbo-suporte + substantivo deverbal, e locuções fixas."""
    saida = []
    baixa = frase.lower()
    for loc, sug in LEXICO["locucoes_fixas"].items():
        if _ocorre(loc, baixa):
            saida.append((loc, sug))
    verbos = "|".join(sorted(map(re.escape, LEXICO["verbos_suporte"]), key=len, reverse=True))
    for m in re.finditer(rf"(?<![\wÀ-ÿ])({verbos})\s+(?:{ARTIGOS}\s+)?([\wÀ-ÿ]+)", baixa):
        verbo, nome = m.group(1), m.group(2)
        if nome in LEXICO["deverbais"] and verbo not in SUPORTE_FRACO:
            saida.append((m.group(0), LEXICO["deverbais"][nome]))
        elif RE_NOMINAL.search(nome) and len(nome) > 5:
            saida.append((m.group(0), LEXICO["deverbais"].get(nome, "o verbo correspondente")))
    return saida


AUX_PASSIVA = r"é|são|foi|foram|será|serão|seja|sejam|era|eram|fosse|fossem|ser|sido|sendo|seria|seriam"
RE_PASSIVA = re.compile(
    rf"(?<![\wÀ-ÿ])({AUX_PASSIVA})\s+(?:[\wÀ-ÿ]+mente\s+)?([\wÀ-ÿ]+(?:ado|ada|ados|adas|ido|ida|idos|idas|ito|ita|itos|itas|osto|osta|eito|eita))(?![\wÀ-ÿ])(\s+pel[oa]s?|\s+por)?",
    re.I)
PART_ADJ = set(LEXICO["participios_adjetivos"])

NAO_SIGLAS = {"OU", "NO", "NA", "DE", "DO", "DA", "EM", "SE", "UM", "OS", "AS", "AO", "OK", "EU"}
RE_SIGLA = re.compile(r"(?<![\wÀ-ÿ])([A-Z][A-Z0-9]{1,5})(s?)(?![\wÀ-ÿ])")


def verificar(texto: str, perfil: str = "T") -> dict:
    perfil = perfil.upper()
    niveis = MATRIZ[perfil]
    blocos, siglas_decl, achados = ler_blocos(texto)
    excecoes_aplicadas = []
    conhecidas = set(LEXICO["siglas_conhecidas"]) | siglas_decl
    siglas_vistas: dict[str, bool] = {}

    def add(regra, conf, bloco: Bloco, trecho, msg, sug=""):
        if regra not in niveis:
            return
        if regra in bloco.excecoes:
            excecoes_aplicadas.append({"regra": regra, "linha": bloco.linha, "motivo": bloco.excecoes[regra]})
            return
        achados.append(Achado(regra, niveis[regra], conf, bloco.linha, resumo(trecho), msg, sug))

    for a in achados:  # achados do parser (PTC-24)
        a.nivel = niveis.get(a.regra, "R")
    achados[:] = [a for a in achados if a.regra in niveis]

    for b in blocos:
        limpo = limpar_inline(b.texto)
        frases = dividir_frases(limpo)

        # PTC-21 — aviso sem consequência
        m = re.match(rf"^({'|'.join(LEXICO['rotulos_aviso'])})\s*[:!.—-]\s*(.*)$", limpo, re.I)
        if m:
            resto = m.group(2).lower()
            if not resto or not any(_ocorre(c, resto) for c in LEXICO["marcadores_consequencia"]):
                add("PTC-21", "media", b, limpo, f"O aviso “{m.group(1)}” não descreve risco nem consequência.",
                    "Diga o que acontece se o leitor ignorar o aviso: “Não desligue o servidor: a base pode corromper.”")

        # PTC-15 — parágrafo com mais de 6 frases
        if b.tipo == "paragrafo" and len(frases) > 6:
            add("PTC-15", "alta", b, frases[0], f"Parágrafo com {len(frases)} frases (máximo 6).",
                "Divida o parágrafo por assunto.")

        # PTC-18 — passo numerado sem imperativo
        if b.tipo == "item_numerado" and frases:
            prim = (palavras(frases[0]) or [""])[0]
            if re.fullmatch(r"[a-zà-ÿ]{3,}(ar|er|ir|or)", prim) and prim not in {"por", "para", "antes", "depois", "maior", "menor", "exterior", "interior"}:
                add("PTC-18", "media", b, frases[0], f"O passo começa com o infinitivo “{prim}”.",
                    "Use o imperativo: “Selecione”, “Confirme”, “Verifique”.")
            elif re.match(r"^(deve-se|é necessário|é preciso|o usuário deve|você deve)", frases[0], re.I):
                add("PTC-18", "media", b, frases[0], "O passo não usa o imperativo.", "Comece pelo verbo no imperativo.")

        for f in frases:
            n = contar_palavras(f)
            if b.tipo == "item_numerado":
                if n > 20:
                    add("PTC-03", "alta", b, f, f"Instrução com {n} palavras (máximo 20).",
                        "Divida em duas instruções ou registre uma exceção.")
            elif n > 25:
                add("PTC-04", "alta", b, f, f"Frase com {n} palavras (máximo 25).", "Divida a frase.")

            for trecho, sug in regra_nominalizacao(f):
                add("PTC-11", "media", b, f, f"Locução com substantivo abstrato: “{trecho}”.", f"Prefira: {sug}.")

            fl = f.lower()
            tem_numero = bool(re.search(r"\d", f))
            for v in LEXICO["vagas"]:
                if _ocorre(v, fl):
                    add("PTC-12", "baixa" if tem_numero else "media", b, f, f"Expressão vaga: “{v}”.",
                        "Troque por um critério mensurável (valor, prazo, condição).")

            for pm in RE_PASSIVA.finditer(f):
                if pm.group(2).lower() in PART_ADJ:
                    continue
                conf = "media" if pm.group(3) else "baixa"
                add("PTC-05", conf, b, f, f"Possível voz passiva: “{pm.group(0).strip()}”.",
                    "Se o agente for conhecido, use a voz ativa: “O sistema valida o arquivo.”")

            pal = palavras(f)
            neg = sum(1 for p in pal if p in LEXICO["negacoes"])
            sub = sum(1 for p in pal if p in LEXICO["subordinadores"])
            if neg >= 2:
                add("PTC-23", "media", b, f, f"Frase com {neg} negações.", "Reescreva na forma afirmativa ou divida.")
            if sub >= 3:
                add("PTC-23", "baixa", b, f, f"Frase com {sub} conectivos de subordinação.", "Divida a frase.")

        # PTC-17 — sigla sem definição na primeira ocorrência
        for sm in RE_SIGLA.finditer(limpo):
            sigla = sm.group(1)
            if sigla in NAO_SIGLAS or sigla in conhecidas or sigla + sm.group(2) in conhecidas or sigla in siglas_vistas:
                continue
            if not re.search(r"[A-Z].*[A-Z]", sigla) or sigla.isdigit():
                continue
            ini, fim = sm.span()
            antes, depois = limpo[max(0, ini - 2):ini], limpo[fim:fim + 3]
            definida = "(" in antes or depois.lstrip().startswith(("(", "—", "–", ":")) or \
                re.search(rf"\(\s*{sigla}s?\s*\)", limpo[:ini + len(sigla) + 3]) is not None
            siglas_vistas[sigla] = definida
            if not definida:
                add("PTC-17", "media", b, limpo[max(0, ini - 40):fim + 40],
                    f"Sigla “{sigla}” sem definição na primeira ocorrência.",
                    f"Escreva o nome completo e a sigla entre parênteses, ou declare <!-- ptc-siglas: {sigla} -->.")

    achados.sort(key=lambda a: (a.linha, a.regra))
    obrig_alta = [a for a in achados if a.nivel == "O" and a.confianca == "alta"]
    obrig = [a for a in achados if a.nivel == "O"]
    por_regra: dict[str, int] = {}
    for a in achados:
        por_regra[a.regra] = por_regra.get(a.regra, 0) + 1
    return {
        "spec_version": SPEC_VERSION,
        "perfil": f"PTC-{perfil}",
        "blocos_verificados": len(blocos),
        "achados": [asdict(a) for a in achados],
        "excecoes_aplicadas": excecoes_aplicadas,
        "resumo": {
            "total": len(achados),
            "por_regra": dict(sorted(por_regra.items())),
            "obrigatorias": len(obrig),
            "obrigatorias_alta_confianca": len(obrig_alta),
            "classificacao_preliminar": "Não conforme" if obrig_alta else (
                "Revisar" if obrig else "Sem violação automática"),
        },
        "observacao": "Classificação preliminar: regras de julgamento (J) não são verificadas por este script.",
    }


def filtrar(resultado: dict, min_conf: str) -> dict:
    lim = CONFIANCA[min_conf]
    resultado["achados"] = [a for a in resultado["achados"] if CONFIANCA[a["confianca"]] >= lim]
    return resultado


def imprimir(res: dict) -> None:
    r = res["resumo"]
    print(f"PTC-BR {res['spec_version']} · perfil {res['perfil']} · {res['blocos_verificados']} blocos")
    print(f"Achados: {r['total']} · obrigatórias: {r['obrigatorias']} "
          f"(alta confiança: {r['obrigatorias_alta_confianca']}) · {r['classificacao_preliminar']}\n")
    for a in res["achados"]:
        print(f"L{a['linha']:<5} {a['regra']} [{a['nivel']}/{a['confianca']}] {a['mensagem']}")
        print(f"        › {a['trecho']}")
        if a["sugestao"]:
            print(f"        ✎ {a['sugestao']}")
    for e in res["excecoes_aplicadas"]:
        print(f"L{e['linha']:<5} {e['regra']} exceção registrada: {e['motivo']}")
    print(f"\n{res['observacao']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verificador PTC-BR (regras automáticas e parciais).")
    ap.add_argument("arquivo", nargs="?", help="Arquivo .md/.txt ou '-' para stdin")
    ap.add_argument("--texto", help="Texto a verificar, em vez de arquivo")
    ap.add_argument("--perfil", default="T", choices=["L", "T", "C", "l", "t", "c"])
    ap.add_argument("--json", action="store_true", help="Saída em JSON")
    ap.add_argument("--min-confianca", default="baixa", choices=list(CONFIANCA))
    args = ap.parse_args(argv)

    try:
        if args.texto is not None:
            texto = args.texto
        elif args.arquivo in (None, "-"):
            texto = sys.stdin.read()
        else:
            texto = Path(args.arquivo).read_text(encoding="utf-8-sig")
    except OSError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2

    res = filtrar(verificar(texto, args.perfil), args.min_confianca)
    if args.json:
        json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        imprimir(res)
    return 1 if res["resumo"]["obrigatorias_alta_confianca"] else 0


if __name__ == "__main__":
    sys.exit(main())
