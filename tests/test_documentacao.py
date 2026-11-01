"""O projeto segue as próprias regras: a documentação para pessoas passa no verificador PTC-BR.

Falha se um documento tiver achado de confiança média ou alta. Achados de confiança baixa são
dicas de revisão (ex.: voz passiva com agente irrelevante) e ficam permitidos.
Os evals/ ficam de fora: eles contêm texto ruim de propósito, como entrada de teste.
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "skills" / "ptc-br" / "scripts"))
import ptc_check as pc  # noqa: E402

DOCUMENTOS = [
    "README.md",
    "CHANGELOG.md",
    "skills/ptc-br/SKILL.md",
    "skills/ptc-br/references/regras.md",
    "skills/ptc-br/references/rubrica-judge.md",
]


class DocumentacaoConforme(unittest.TestCase):
    def test_documentos(self):
        for doc in DOCUMENTOS:
            with self.subTest(doc):
                res = pc.verificar((RAIZ / doc).read_text(encoding="utf-8"), "T")
                serios = [f"L{a['linha']} {a['regra']} [{a['confianca']}] {a['mensagem']}"
                          for a in res["achados"] if a["confianca"] in ("alta", "media")]
                self.assertEqual(serios, [], f"{doc} não segue o PTC-BR:\n  " + "\n  ".join(serios))


if __name__ == "__main__":
    unittest.main()
