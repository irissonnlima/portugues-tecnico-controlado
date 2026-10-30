"""Testes do vocabulário controlado (0.2.0)."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "skills" / "ptc-br" / "scripts"))
sys.path.insert(0, str(RAIZ / "tools"))
import ptc_check as pc  # noqa: E402

try:
    import yaml  # noqa: F401
    import compilar_vocabulario as cv
except ImportError:  # PyYAML só é necessário para quem edita o vocabulário
    cv = None

VERBETES = json.loads((RAIZ / "skills/ptc-br/scripts/vocabulario.json").read_text(encoding="utf-8"))["verbetes"]


def achados(texto, regra=None):
    return [a for a in pc.verificar(texto)["achados"] if regra is None or a["regra"] == regra]


@unittest.skipIf(cv is None, "PyYAML ausente")
class Compilacao(unittest.TestCase):
    def test_json_sincronizado_com_yaml(self):
        r = subprocess.run([sys.executable, str(RAIZ / "tools/compilar_vocabulario.py"), "--checar"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_flexao_regular_e_ortografia(self):
        self.assertIn("verifique", cv.flexionar_verbo("verificar"))
        self.assertIn("chegue", cv.flexionar_verbo("chegar"))
        self.assertIn("comece", cv.flexionar_verbo("começar"))
        self.assertIn("conheça", cv.flexionar_verbo("conhecer"))
        self.assertIn("utilizando", cv.flexionar_verbo("utilizar"))

    def test_plural(self):
        self.assertEqual(cv.flexionar_nome("operação"), ["operação", "operações"])
        self.assertIn("servidores", cv.flexionar_nome("servidor"))
        self.assertIn("índices", cv.flexionar_nome("índice"))


class ExemplosDosVerbetes(unittest.TestCase):
    """Cada verbete detectável: o exemplo incorreto dispara, o correto não."""

    def test_exemplos(self):
        for v in VERBETES:
            if v["status"] == "aprovado" or v.get("sentidos"):
                continue
            with self.subTest(v["id"]):
                if v.get("exemplo_incorreto"):
                    ids = [a["mensagem"] for a in achados(v["exemplo_incorreto"], v["regra"])]
                    self.assertTrue(any(v["id"] in m for m in ids), f"{v['id']} não detectou: {v['exemplo_incorreto']}")
                if v.get("exemplo_correto"):
                    ids = [a["mensagem"] for a in achados(v["exemplo_correto"], v["regra"])]
                    self.assertFalse(any(v["id"] in m for m in ids), f"{v['id']} disparou no correto: {v['exemplo_correto']}")


class Deteccao(unittest.TestCase):
    def test_nivel_por_status(self):
        conf = {a["mensagem"].split("(")[-1].rstrip(").") : (a["nivel"], a["confianca"])
                for a in achados("Utilize o token. A nível de servidor, confira o log.")}
        self.assertEqual(conf["V-0100"], ("R", "media"))   # não preferido
        self.assertEqual(conf["V-0210"], ("O", "alta"))    # proibido: obrigatória em qualquer perfil
        self.assertEqual(conf["V-0114"], ("R", "baixa"))   # em análise

    def test_o_mesmo_adjetivo_nao_dispara(self):
        self.assertEqual(achados("Use o mesmo nome nos dois ambientes.", "PTC-07"), [])

    def test_o_mesmo_predicativo_nao_dispara(self):
        self.assertEqual(achados("O contrato é sempre o mesmo.", "PTC-07"), [])

    def test_pode_estar_ocorrendo_nao_e_gerundismo(self):
        self.assertFalse([a for a in achados("O erro pode estar ocorrendo no proxy.") if "V-0301" in a["mensagem"]])

    def test_auxiliar_adjetivo_nao_dispara(self):
        self.assertFalse([a for a in achados("Crie uma tabela auxiliar.") if "V-0108" in a["mensagem"]])

    def test_polissemico_vai_para_relatorio_e_nao_para_achados(self):
        res = pc.verificar("Suba o container. Depois suba o CSV.")
        self.assertEqual(res["vocabulario_polissemico"][0]["lema"], "subir")
        self.assertEqual(res["vocabulario_polissemico"][0]["ocorrencias"], 2)
        self.assertFalse([a for a in res["achados"] if "V-0400" in a["mensagem"]])

    def test_perfil_C_torna_ptc25_obrigatoria(self):
        r = [a for a in pc.verificar("Utilize o token.", "C")["achados"] if a["regra"] == "PTC-25"]
        self.assertEqual(r[0]["nivel"], "O")


if __name__ == "__main__":
    unittest.main()
