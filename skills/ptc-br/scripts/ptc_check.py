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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ptc_vocab  # noqa: E402

SPEC_VERSION = "0.4.0"
LEXICO = json.loads((Path(__file__).with_name("lexico.json")).read_text(encoding="utf-8"))
_VOCAB_ARQ = Path(__file__).with_name("vocabulario.json")


DETERMINANTES = {
    # determinantes que denunciam o gênero oposto ao registrado no glossário
    "m": r"a|as|da|das|na|nas|uma|umas|pela|pelas|esta|estas|essa|essas|nesta|nessa|desta|dessa|sua|suas|nova|novas|primeira|última",
    "f": r"o|os|do|dos|no|nos|um|uns|pelo|pelos|este|estes|esse|esses|neste|nesse|deste|desse|seu|seus|novo|novos|primeiro|último",
}


def preparar_vocabulario(verbetes: list[dict]) -> list[dict]:
    """Compila a regex de cada verbete (a camada do time pode ter mudado ou acrescentado verbetes)."""
    saida = []
    for v in verbetes:
        v = dict(v)
        v["_re"] = re.compile(v.get("regex") or ptc_vocab.regex_do_verbete(v), re.I)
        if v.get("genero") in DETERMINANTES:
            v["_re_genero"] = re.compile(rf"(?<![\wÀ-ÿ])(?:{DETERMINANTES[v['genero']]})\s+(?:{v['_re'].pattern})", re.I)
        saida.append(v)
    return saida


def criar_lematizador():
    """Devolve uma função palavra → lema usando simplemma, ou levanta ImportError."""
    from functools import lru_cache

    import simplemma

    @lru_cache(maxsize=20000)
    def lematizar(palavra: str) -> str:
        return simplemma.lemmatize(palavra, lang="pt").lower()
    return lematizar


VOCABULARIO_GERAL = json.loads(_VOCAB_ARQ.read_text(encoding="utf-8"))["verbetes"] if _VOCAB_ARQ.exists() else []
VOCABULARIO = preparar_vocabulario(VOCABULARIO_GERAL)


def carregar_camadas(caminhos: list[str]) -> tuple[list[dict], set[str], list[str]]:
    """Aplica as camadas na ordem dada (a última vence). Devolve verbetes, siglas e nomes das camadas."""
    verbetes, siglas, nomes = VOCABULARIO_GERAL, set(), []
    for c in caminhos:
        camada = ptc_vocab.carregar_camada(c)
        verbetes, s = ptc_vocab.aplicar_camada(verbetes, camada)
        siglas |= s
        nomes.append(camada["nome"])
    return preparar_vocabulario(verbetes), siglas, nomes

# Nível de cada regra por perfil (seção 3.1 da spec). Ausente = não se aplica.
MATRIZ = {
    "L": {"PTC-03": "R", "PTC-05": "R", "PTC-07": "O", "PTC-08": "R", "PTC-11": "R", "PTC-12": "R", "PTC-17": "R",
          "PTC-18": "R", "PTC-21": "O", "PTC-23": "R", "PTC-25": "R", "PTC-26": "R"},
    "T": {"PTC-03": "O", "PTC-04": "R", "PTC-05": "O", "PTC-07": "O", "PTC-08": "O", "PTC-11": "R", "PTC-12": "R",
          "PTC-15": "R", "PTC-17": "O", "PTC-18": "O", "PTC-21": "O", "PTC-23": "R", "PTC-24": "O",
          "PTC-25": "R", "PTC-26": "O"},
    "C": {"PTC-03": "O", "PTC-04": "O", "PTC-05": "O", "PTC-07": "O", "PTC-08": "O", "PTC-11": "O", "PTC-12": "O",
          "PTC-15": "O", "PTC-17": "O", "PTC-18": "O", "PTC-21": "O", "PTC-23": "O", "PTC-24": "O",
          "PTC-25": "O", "PTC-26": "O"},
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
    ignorado: str = ""                               # motivo, quando o bloco fica fora da verificação


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
RE_DIRETIVA = re.compile(
    r"ptc-(?P<nome>ignorar-inicio|ignorar-fim|ignorar|idioma-inicio|idioma-fim|idioma|mencoes)\b\s*:?\s*(?P<valor>.*?)\s*-->",
    re.I)


def ler_blocos(texto: str) -> tuple[list[Bloco], set[str], list[Achado], dict]:
    """Divide o markdown em blocos verificáveis. Ignora código, tabelas, títulos e front matter.

    Também lê as diretivas em comentário HTML: ptc-excecao, ptc-siglas, ptc-ignorar[-inicio|-fim],
    ptc-idioma[-inicio|-fim] e ptc-mencoes. Devolve (blocos, siglas, achados, meta)."""
    linhas = texto.splitlines()
    blocos: list[Bloco] = []
    siglas_decl: set[str] = set()
    achados: list[Achado] = []
    meta = {"ignorados": [], "mencoes": set()}
    atual: Bloco | None = None
    excecao_pendente: dict = {}
    ignorar_pendente = ""     # vale para o próximo bloco
    regiao_ignorada = ""      # vale até a diretiva de fim
    em_codigo = False
    em_comentario = ""
    i = 0

    def fechar():
        nonlocal atual
        if atual and atual.texto.strip():
            if atual.ignorado:
                meta["ignorados"].append({"linha": atual.linha, "motivo": atual.ignorado})
            else:
                blocos.append(atual)
        atual = None

    def novo(tipo: str, n: int, conteudo: str) -> Bloco:
        nonlocal excecao_pendente, ignorar_pendente
        b = Bloco(tipo, n, conteudo, excecao_pendente, ignorar_pendente or regiao_ignorada)
        excecao_pendente, ignorar_pendente = {}, ""
        return b

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
            m = RE_DIRETIVA.search(s)
            if m:
                nome, valor = m.group("nome").lower(), m.group("valor").strip()
                motivo = valor or "ignorado"
                if nome == "ignorar":
                    ignorar_pendente = f"ignorar: {motivo}"
                elif nome == "ignorar-inicio":
                    regiao_ignorada = f"ignorar: {motivo}"
                elif nome in ("ignorar-fim", "idioma-fim"):
                    regiao_ignorada = ""
                elif nome == "idioma" and valor.lower() not in ("pt", "pt-br"):
                    ignorar_pendente = f"idioma: {valor.lower()}"
                elif nome == "idioma-inicio" and valor.lower() not in ("pt", "pt-br"):
                    regiao_ignorada = f"idioma: {valor.lower()}"
                elif nome == "mencoes":
                    meta["mencoes"] |= {x.strip().lower() for x in valor.split(",") if x.strip()}
            continue

        if not s:
            fechar()
            continue
        if s.startswith("#"):
            # um título também define siglas: "# PTC-BR — Português Técnico Controlado" ou "# Nome (SIGLA)"
            m = re.match(r"#+\s*([A-Z][A-Z0-9]{1,5})[\w-]*\s*[—–:-]\s+\S", s)
            if m:
                siglas_decl.add(m.group(1))
            siglas_decl.update(re.findall(r"\(([A-Z][A-Z0-9]{1,5})s?\)", s))
            fechar()
            continue
        if s.startswith("|") or re.fullmatch(r"[-*_ ]{3,}", s):
            fechar()
            continue

        m = RE_LISTA.match(linha)
        if m:
            fechar()
            tipo = "item_numerado" if m.group(2)[0].isdigit() else "item"
            atual = novo(tipo, n, m.group(3))
            continue

        if s.startswith(">"):
            conteudo = s.lstrip(">").strip()
            if atual and atual.tipo == "citacao":
                atual.texto += " " + conteudo
            else:
                fechar()
                atual = novo("citacao", n, conteudo)
            continue

        if atual and (atual.tipo in ("paragrafo",) or linha.startswith((" ", "\t"))):
            atual.texto += " " + s
        else:
            fechar()
            atual = novo("paragrafo", n, s)
    fechar()
    return blocos, siglas_decl, achados, meta


MENCAO_TOKEN = "⟦menção⟧"
RE_PERCENTUAL = re.compile(
    r"^\s*\(\s*(?:~|≈|cerca de\s+)?(\d+(?:[.,]\d+)?)\s*%?\s*(?:(?:–|—|-|a)\s*(\d+(?:[.,]\d+)?)\s*)?%\s*\)")


def _num(x: str) -> float:
    return float(x.replace(",", "."))


def _faixa(v: dict) -> str:
    lo, hi = v["probabilidade"]
    return f"{lo:g}–{hi:g}%"


def mascarar_mencoes(texto: str, tipos: set[str]) -> str:
    """Troca menções metalinguísticas (*utilizar*, "a nível de") por um token: elas citam o termo, não o usam."""
    if "italico" in tipos or "itálico" in tipos:
        texto = re.sub(r"(?<![*\w])\*(?!\*)([^*\n]+?)\*(?![*\w])", MENCAO_TOKEN, texto)
        texto = re.sub(r"(?<![_\w])_(?!_)([^_\n]+?)_(?![_\w])", MENCAO_TOKEN, texto)
    if "aspas" in tipos:
        texto = re.sub(r"“[^”\n]+”|\"[^\"\n]+\"", MENCAO_TOKEN, texto)
    return texto


EN_STOP = set("""the of and to in is are for with this that it be by on from an or not you your will can if when
should must all any each which has have was were at its into than then there these those we our does""".split())
PT_STOP = set("""o os de da dos das que é em na nos nas um uma para com não por se ao à aos às mais como pelo
pela pelos pelas seu sua seus suas este esta isso esse essa ou""".split())
# "do", "no", "a", "as" existem nas duas línguas: não contam para nenhum lado


def parece_ingles(texto: str) -> bool:
    """Heurística por palavras funcionais. Termos técnicos em inglês dentro de frase em português não contam."""
    pal = re.findall(r"[A-Za-zÀ-ÿ']+", texto.lower())
    en = sum(1 for p in pal if p in EN_STOP)
    pt = sum(1 for p in pal if p in PT_STOP)
    return (len(pal) >= 3 and en >= 1 and pt == 0) or (en >= 2 and en >= 4 * pt)


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
        if b in (CODE_TOKEN, URL_TOKEN, MENCAO_TOKEN):
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
# substantivos em -ção que nomeiam um objeto, não uma ação: "execute a aplicação" é natural
NOMES_DE_OBJETO = {"operação", "operações", "aplicação", "aplicações", "função", "funções", "instrução", "instruções",
                   "transação", "transações", "migração", "migrações", "integração", "integrações"}


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
        elif RE_NOMINAL.search(nome) and len(nome) > 5 and not (verbo in SUPORTE_FRACO and nome in NOMES_DE_OBJETO):
            saida.append((m.group(0), LEXICO["deverbais"].get(nome, "o verbo correspondente")))
    return saida


AUX_PASSIVA = r"é|são|foi|foram|será|serão|seja|sejam|era|eram|fosse|fossem|ser|sido|sendo|seria|seriam"
RE_PASSIVA = re.compile(
    rf"(?<![\wÀ-ÿ])({AUX_PASSIVA})\s+(?:[\wÀ-ÿ]+mente\s+)?([\wÀ-ÿ]+(?:ado|ada|ados|adas|ido|ida|idos|idas|ído|ída|ídos|ídas|ito|ita|itos|itas|osto|osta|eito|eita))(?![\wÀ-ÿ])(\s+pel[oa]s?|\s+por)?",
    re.I)
PART_ADJ = set(LEXICO["participios_adjetivos"])

NEGADORES = {"não", "nunca", "jamais", "sem"}
CONCORDANTES = {"nada", "nem", "nenhum", "nenhuma", "nenhuns", "nenhumas", "ninguém", "tampouco"}


def negacoes_logicas(oracao: str) -> int:
    """Conta negações lógicas. Em pt-BR, 'não… nada' e 'não há X nem Y' formam UMA negação (concordância
    negativa): o concordante só conta quando nenhum negador apareceu antes na oração."""
    total, negou = 0, False
    for p in palavras(oracao):
        if p in NEGADORES:
            total, negou = total + 1, True
        elif p in CONCORDANTES and not negou:
            total, negou = total + 1, True
    return total


NAO_SIGLAS = {"OU", "NO", "NA", "DE", "DO", "DA", "EM", "SE", "UM", "OS", "AS", "AO", "OK", "EU"}
RE_SIGLA = re.compile(r"(?<![\wÀ-ÿ])([A-Z][A-Z0-9]{1,5})(s?)(?![\wÀ-ÿ])")


def verificar(texto: str, perfil: str = "T", siglas_extra: set[str] | None = None,
              vocabulario: list[dict] | None = None, camadas: list[str] | None = None,
              lematizar=None, detectar_idioma: bool = True) -> dict:
    perfil = perfil.upper()
    niveis = MATRIZ[perfil]
    blocos, siglas_decl, achados, meta = ler_blocos(texto)
    ignorados = meta["ignorados"]
    excecoes_aplicadas = []
    conhecidas = set(LEXICO["siglas_conhecidas"]) | siglas_decl | (siglas_extra or set())
    vocab = VOCABULARIO if vocabulario is None else vocabulario
    por_lema = {v["lema"].lower(): v for v in vocab if v.get("lematizavel")} if lematizar else {}
    escala = sorted((v for v in vocab if v.get("probabilidade")), key=lambda v: v["probabilidade"][0])
    siglas_vistas: dict[str, bool] = {}

    polissemicos: dict[str, dict] = {}

    def add(regra, conf, bloco: Bloco, trecho, msg, sug="", nivel=None):
        if regra not in niveis:
            return
        if regra in bloco.excecoes:
            excecoes_aplicadas.append({"regra": regra, "linha": bloco.linha, "motivo": bloco.excecoes[regra]})
            return
        achados.append(Achado(regra, nivel or niveis[regra], conf, bloco.linha, resumo(trecho), msg, sug))

    for a in achados:  # achados do parser (PTC-24)
        a.nivel = niveis.get(a.regra, "R")
    achados[:] = [a for a in achados if a.regra in niveis]

    for b in blocos:
        limpo = limpar_inline(mascarar_mencoes(b.texto, meta["mencoes"]) if meta["mencoes"] else b.texto)
        if detectar_idioma and parece_ingles(limpo):
            ignorados.append({"linha": b.linha, "motivo": "idioma detectado: en"})
            continue
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
            if (re.fullmatch(r"[a-zà-ÿ]{3,}(ar|er|ir)", prim) or prim in {"pôr", "compor", "repor", "dispor", "propor"}) \
                    and prim not in {"lugar", "valor", "familiar", "similar", "particular", "popular", "regular", "mar", "par", "bar"}:
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
            for v in LEXICO["quantificadores_vagos"]:
                if _ocorre(v, fl):
                    add("PTC-12", "baixa", b, f, f"Quantidade vaga: “{v}”.",
                        "Se a quantidade importar para o leitor, informe o número ou liste os itens.")

            for pm in RE_PASSIVA.finditer(f):
                part = pm.group(2).lower()
                if part in PART_ADJ or (re.search(r"[áéóúâêô]", part) and not re.search(r"[íú]d[oa]s?$", part)):
                    continue   # válido, rápido: adjetivo; incluído, construído: particípio
                conf = "media" if pm.group(3) else "baixa"
                add("PTC-05", conf, b, f, f"Possível voz passiva: “{pm.group(0).strip()}”.",
                    "Se o agente for conhecido, use a voz ativa: “O sistema valida o arquivo.”")

            # PTC-25 (e regras dos padrões) — vocabulário controlado
            ocorrencias = [(v, vm.group(0), "", vm.start(), vm.end()) for v in vocab for vm in v["_re"].finditer(f)
                           # palavra toda em maiúsculas (DELETE, UPDATE) é palavra-chave ou sigla, não o termo
                           if v.get("padrao") or not (vm.group(0).isupper() and len(vm.group(0)) >= 3)]
            if lematizar:   # formas que a flexão automática não gera (fez, dispõe, utilizaremos)
                ja = {(o[0]["id"], o[1].lower()) for o in ocorrencias}
                for tm in re.finditer(r"[\wÀ-ÿ]+", f):
                    v = por_lema.get(lematizar(tm.group(0).lower()))
                    if v and (v["id"], tm.group(0).lower()) not in ja:
                        ocorrencias.append((v, tm.group(0), " — por lema", tm.start(), tm.end()))
                        ja.add((v["id"], tm.group(0).lower()))
            # uma ocorrência dentro de outra maior não conta ("provável" dentro de "muito provável")
            ocorrencias = [o for o in ocorrencias
                           if not any(p[3] <= o[3] and o[4] <= p[4] and p[4] - p[3] > o[4] - o[3] for p in ocorrencias)]
            for v in vocab:   # PTC-08: gênero diferente do registrado no glossário
                if v.get("_re_genero"):
                    for gm in v["_re_genero"].finditer(f):
                        art = "o" if v["genero"] == "m" else "a"
                        add("PTC-08", "media", b, f,
                            f"Gênero diferente do glossário: “{gm.group(0)}” (glossário: {art} {v['lema']}, {v['id']}).",
                            f"Use o gênero do glossário{' de ' + v['dominio'] if v.get('dominio') else ''}: "
                            f"{art} {v['lema']}.")
            for v, encontrado, via, _ini, fim in ocorrencias:
                if v.get("probabilidade"):   # PTC-26: termo da escala exige percentual coerente
                    lo, hi = v["probabilidade"]
                    pm = RE_PERCENTUAL.match(f[fim:])
                    if not pm:
                        add(v.get("regra", "PTC-26"), "alta", b, f,
                            f"Termo de probabilidade sem percentual: “{encontrado}” ({v['id']}).",
                            f"Escreva a faixa entre parênteses: “{encontrado} ({_faixa(v)})”.")
                        continue
                    a = _num(pm.group(1))
                    z = _num(pm.group(2)) if pm.group(2) else a
                    if not (lo <= a <= z <= hi):
                        meio = (a + z) / 2
                        certo = next((e for e in escala if e["probabilidade"][0] <= meio <= e["probabilidade"][1]), None)
                        dica = f"“{certo['lema']} ({_faixa(certo)})”" if certo else "um termo da escala"
                        add(v.get("regra", "PTC-26"), "alta", b, f,
                            f"Percentual incoerente: “{encontrado}” vale {_faixa(v)}, mas o texto diz "
                            f"{pm.group(0).strip()} ({v['id']}).",
                            f"Para esse número, use {dica}; ou corrija o percentual.")
                    continue
                if v.get("sentidos"):
                    reg = polissemicos.setdefault(v["id"], {"id": v["id"], "lema": v["lema"], "ocorrencias": 0,
                                                            "linhas": [], "sentidos": v["sentidos"]})
                    reg["ocorrencias"] += 1
                    if b.linha not in reg["linhas"]:
                        reg["linhas"].append(b.linha)
                    continue
                if v["status"] == "aprovado":
                    continue
                conf = {"proibido": "alta", "nao_preferido": "media"}.get(v["status"], "baixa")
                rotulo = {"proibido": "Termo proibido", "em_analise": "Termo em análise"}.get(v["status"], "Termo não preferido")
                if v["classe"] == "padrao":
                    rotulo = "Construção não preferida"
                origem = f"{v['id']}, camada {v['camada']}" if v.get("camada") else v["id"]
                add(v.get("regra", "PTC-25"), conf, b, f, f"{rotulo}: “{encontrado}” ({origem}){via}.",
                    f"Prefira: {', '.join(v['preferir'])}." + (f" {v['motivo']}" if v.get("motivo") else ""),
                    nivel="O" if v["status"] == "proibido" else None)

            pal = palavras(f)
            sub = sum(1 for p in pal if p in LEXICO["subordinadores"])
            # negações encadeadas na mesma oração ("não é possível não validar", "nunca X sem Y");
            # orações coordenadas ("não resolve e não tem rota") não contam juntas
            oracoes = re.split(r"[,;:—–]|\s(?:e|ou|mas|porém)\s", f.lower())
            pior = max(oracoes, key=negacoes_logicas)
            neg, nao = negacoes_logicas(pior), palavras(pior).count("não")
            if neg >= 3 or nao >= 2:
                add("PTC-23", "media", b, f, f"Oração com {neg} negações encadeadas: “{resumo(pior.strip(), 60)}”.",
                    "Reescreva na forma afirmativa ou divida a frase.")
            elif neg == 2:
                add("PTC-23", "baixa", b, f, f"Negação dupla: “{resumo(pior.strip(), 60)}”.",
                    "Considere a forma afirmativa: “Nunca entregue X sem Y” → “Sempre entregue X com Y”.")
            if sub >= 3:
                add("PTC-23", "baixa", b, f, f"Frase com {sub} conectivos de subordinação.", "Divida a frase.")

        # PTC-17 — sigla sem definição na primeira ocorrência
        for sm in RE_SIGLA.finditer(limpo):
            sigla = sm.group(1)
            if sigla in NAO_SIGLAS or sigla in conhecidas or sigla + sm.group(2) in conhecidas or sigla in siglas_vistas:
                continue
            if not re.search(r"[A-Z].*[A-Z]", sigla) or sigla.isdigit() or len(set(sigla)) == 1:
                continue   # NN, XX: marcador de posição, não sigla
            ini, fim = sm.span()
            antes, depois = limpo[max(0, ini - 2):ini], limpo[fim:fim + 3]
            if re.match(r"\.[a-z]{1,5}\b", limpo[fim:fim + 7]):   # nome de arquivo: SKILL.md, README.txt
                continue
            # caixa alta de ênfase (LEIA, NUNCA, DEPENDE) parece palavra, não sigla: confiança baixa
            enfase = len(sigla) >= 4 and sum(c in "AEIOU" for c in sigla) >= 2
            definida = "(" in antes or re.match(r"[\w-]*\s*[(—–:]", limpo[fim:fim + 15]) is not None or \
                re.search(rf"\(\s*{sigla}s?\s*\)", limpo[:ini + len(sigla) + 3]) is not None
            siglas_vistas[sigla] = definida
            if not definida:
                add("PTC-17", "baixa" if enfase else "media", b, limpo[max(0, ini - 40):fim + 40],
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
        "camadas": camadas or [],
        "lematizacao": bool(lematizar),
        "blocos_verificados": len(blocos),
        "achados": [asdict(a) for a in achados],
        "excecoes_aplicadas": excecoes_aplicadas,
        "blocos_ignorados": sorted(ignorados, key=lambda x: x["linha"]),
        "vocabulario_polissemico": sorted(polissemicos.values(), key=lambda x: -x["ocorrencias"]),
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
    camadas = f" · camadas: {', '.join(res['camadas'])}" if res.get("camadas") else ""
    print(f"PTC-BR {res['spec_version']} · perfil {res['perfil']} · {res['blocos_verificados']} blocos{camadas}")
    print(f"Achados: {r['total']} · obrigatórias: {r['obrigatorias']} "
          f"(alta confiança: {r['obrigatorias_alta_confianca']}) · {r['classificacao_preliminar']}\n")
    for a in res["achados"]:
        print(f"L{a['linha']:<5} {a['regra']} [{a['nivel']}/{a['confianca']}] {a['mensagem']}")
        print(f"        › {a['trecho']}")
        if a["sugestao"]:
            print(f"        ✎ {a['sugestao']}")
    for e in res["excecoes_aplicadas"]:
        print(f"L{e['linha']:<5} {e['regra']} exceção registrada: {e['motivo']}")
    if res.get("vocabulario_polissemico"):
        print("\nPalavras com mais de um sentido (confira a consistência — PTC-08):")
        for p in res["vocabulario_polissemico"]:
            sentidos = "; ".join(s["sentido"] for s in p["sentidos"])
            print(f"  {p['lema']} ×{p['ocorrencias']} (linhas {', '.join(map(str, p['linhas'][:8]))}) — {sentidos}")
    if res.get("blocos_ignorados"):
        motivos: dict[str, int] = {}
        for x in res["blocos_ignorados"]:
            motivos[x["motivo"]] = motivos.get(x["motivo"], 0) + 1
        print("\nBlocos fora da verificação: " + "; ".join(f"{m} ×{q}" for m, q in motivos.items()))
    print(f"\n{res['observacao']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verificador PTC-BR (regras automáticas e parciais).")
    ap.add_argument("arquivo", nargs="?", help="Arquivo .md/.txt ou '-' para stdin")
    ap.add_argument("--texto", help="Texto a verificar, em vez de arquivo")
    ap.add_argument("--perfil", default="T", choices=["L", "T", "C", "l", "t", "c"])
    ap.add_argument("--json", action="store_true", help="Saída em JSON")
    ap.add_argument("--min-confianca", default="baixa", choices=list(CONFIANCA))
    ap.add_argument("--vocabulario", action="append", default=[], metavar="CAMADA",
                    help="Camada de vocabulário do time (.yaml ou .json). Pode repetir; a última vence.")
    ap.add_argument("--dominios", default="",
                    help="Restringe os glossários de domínio (ex.: software,dados). Padrão: todos")
    ap.add_argument("--sem-deteccao-idioma", action="store_true",
                    help="Não pula blocos detectados como inglês (a marcação ptc-idioma continua valendo)")
    ap.add_argument("--lematizar", action="store_true",
                    help="Usa lematização (requer simplemma: pip install simplemma) para achar formas irregulares")
    ap.add_argument("--siglas", default="",
                    help="Siglas conhecidas do público: lista separada por vírgula ou caminho de arquivo (uma por linha)")
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

    siglas = set()
    if args.siglas:
        fonte = Path(args.siglas)
        bruto = fonte.read_text(encoding="utf-8") if fonte.is_file() else args.siglas
        siglas = {s.strip() for s in re.split(r"[,\n]", bruto) if s.strip() and not s.strip().startswith("#")}
    vocab, camadas = None, []
    if args.vocabulario:
        try:
            vocab, siglas_camada, camadas = carregar_camadas(args.vocabulario)
        except (OSError, ValueError) as e:
            print(f"erro: {e}", file=sys.stderr)
            return 2
        siglas |= siglas_camada
    if args.dominios:
        quero = {d.strip().lower() for d in args.dominios.split(",") if d.strip()}
        vocab = [v for v in (vocab if vocab is not None else VOCABULARIO) if not v.get("dominio") or v["dominio"] in quero]
    lem = None
    if args.lematizar:
        try:
            lem = criar_lematizador()
        except ImportError:
            print("erro: --lematizar requer simplemma (pip install simplemma)", file=sys.stderr)
            return 2
    res = filtrar(verificar(texto, args.perfil, siglas, vocab, camadas, lem, not args.sem_deteccao_idioma),
                  args.min_confianca)
    if args.json:
        json.dump(res, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        imprimir(res)
    return 1 if res["resumo"]["obrigatorias_alta_confianca"] else 0


if __name__ == "__main__":
    sys.exit(main())
