"""0.6.0: verificação em lote (Action e pre-commit) e registro de aceitação."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ / "skills" / "ptc-br" / "scripts"))
import ptc_lote  # noqa: E402
import ptc_registro  # noqa: E402


def rodar(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        codigo = ptc_lote.main(argv)
    return codigo, buf.getvalue()


class Lote(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        (self.dir / "ruim.md").write_text("1. " + " ".join(["palavra"] * 22) + ".\n\nUtilize o token.\n", encoding="utf-8")
        (self.dir / "bom.md").write_text("Use o token.\n", encoding="utf-8")
        (self.dir / "outro.txt").write_text("Utilize.\n", encoding="utf-8")

    def test_falha_com_obrigatoria_alta(self):
        codigo, saida = rodar([str(self.dir / "ruim.md")])
        self.assertEqual(codigo, 1)
        self.assertIn("PTC-03", saida)

    def test_arquivo_bom_passa(self):
        self.assertEqual(rodar([str(self.dir / "bom.md")])[0], 0)

    def test_falhar_em_nunca(self):
        self.assertEqual(rodar([str(self.dir / "ruim.md"), "--falhar-em", "nunca"])[0], 0)

    def test_falhar_em_qualquer_respeita_min_confianca(self):
        # PTC-25 (média) conta com min-confianca media; some com min-confianca alta + só recomendada
        self.assertEqual(rodar([str(self.dir / "bom.md"), "--falhar-em", "qualquer"])[0], 0)

    def test_so_markdown(self):
        codigo, saida = rodar([str(self.dir / "outro.txt")])
        self.assertEqual(codigo, 0)
        self.assertIn("nenhum arquivo", saida)

    def test_ignorar(self):
        codigo, _ = rodar([str(self.dir / "ruim.md"), "--ignorar", str(self.dir / "ruim*")])
        self.assertEqual(codigo, 0)

    def test_formato_github(self):
        resumo = self.dir / "resumo.md"
        os.environ["GITHUB_STEP_SUMMARY"] = str(resumo)
        try:
            codigo, saida = rodar([str(self.dir / "ruim.md"), "--formato", "github"])
        finally:
            del os.environ["GITHUB_STEP_SUMMARY"]
        self.assertEqual(codigo, 1)
        self.assertIn("::error file=", saida)
        self.assertIn(",line=1,title=PTC-03", saida)
        self.assertIn("| Arquivo |", resumo.read_text(encoding="utf-8"))

    def test_escape_das_anotacoes(self):
        self.assertEqual(ptc_lote.escapar_propriedade("a,b:c%"), "a%2Cb%3Ac%25")
        self.assertEqual(ptc_lote.escapar_dado("x\ny"), "x%0Ay")

    def test_tipo_de_anotacao(self):
        self.assertEqual(ptc_lote.tipo_anotacao({"nivel": "O", "confianca": "alta"}), "error")
        self.assertEqual(ptc_lote.tipo_anotacao({"nivel": "O", "confianca": "baixa"}), "notice")
        self.assertEqual(ptc_lote.tipo_anotacao({"nivel": "R", "confianca": "media"}), "warning")


class Integracao(unittest.TestCase):
    def test_action_declara_entradas(self):
        texto = (RAIZ / "action.yml").read_text(encoding="utf-8")
        for entrada in ("arquivos:", "ignorar:", "perfil:", "vocabulario:", "siglas:", "min-confianca:", "falhar-em:"):
            self.assertIn(entrada, texto)
        self.assertIn("tools/ptc_lote.py", texto)

    def test_pre_commit_aponta_para_script_existente(self):
        texto = (RAIZ / ".pre-commit-hooks.yaml").read_text(encoding="utf-8")
        self.assertIn("entry: tools/ptc_lote.py", texto)
        self.assertTrue((RAIZ / "tools" / "ptc_lote.py").read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"))


class Registro(unittest.TestCase):
    def setUp(self):
        self.reg = Path(tempfile.mkdtemp()) / "sub" / "aceitacao.jsonl"

    def test_registrar_e_resumir(self):
        decisoes = [{"regra": "PTC-25", "decisao": "aceito", "id": "V-0100"}] * 3 + \
                   [{"regra": "PTC-25", "decisao": "descartado", "id": "V-0147", "motivo": "termo citado"}]
        self.assertEqual(ptc_registro.registrar(decisoes, self.reg), 4)
        linha = json.loads(self.reg.read_text(encoding="utf-8").splitlines()[0])
        self.assertIn("data", linha)
        self.assertIn("spec_version", linha)
        res = ptc_registro.resumir(ptc_registro.ler_registros([self.reg]))
        self.assertAlmostEqual(res["por_regra"]["PTC-25"]["taxa_aceitacao"], 0.75)
        self.assertFalse(res["por_regra"]["PTC-25"]["amostra_suficiente"])
        self.assertIn("V-0147", res["verbetes_mais_descartados"])

    def test_nao_guarda_trecho(self):
        ptc_registro.registrar([{"regra": "PTC-03", "decisao": "aceito", "trecho": "texto confidencial"}], self.reg)
        self.assertNotIn("confidencial", self.reg.read_text(encoding="utf-8"))

    def test_regra_a_revisar(self):
        decisoes = [{"regra": "PTC-23", "decisao": "descartado"}] * 8 + [{"regra": "PTC-23", "decisao": "aceito"}] * 2
        ptc_registro.registrar(decisoes, self.reg)
        self.assertEqual(ptc_registro.resumir(ptc_registro.ler_registros([self.reg]))["regras_a_revisar"], ["PTC-23"])

    def test_decisao_invalida(self):
        with self.assertRaisesRegex(ValueError, "decisao"):
            ptc_registro.registrar([{"regra": "PTC-03", "decisao": "talvez"}], self.reg)

    def test_excecoes_no_texto(self):
        pasta = Path(tempfile.mkdtemp())
        (pasta / "a.md").write_text("<!-- ptc-excecao: PTC-03; motivo: x -->\n1. Passo.\n", encoding="utf-8")
        self.assertEqual(ptc_registro.contar_excecoes(pasta)["PTC-03"], 1)

    def test_caminho_padrao_respeita_variavel(self):
        os.environ["PTC_REGISTRO"] = str(self.reg)
        try:
            self.assertEqual(ptc_registro.caminho_padrao(), self.reg)
        finally:
            del os.environ["PTC_REGISTRO"]

    def test_cli_registrar_por_argumentos(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            codigo = ptc_registro.main(["registrar", "--registro", str(self.reg), "--regra", "PTC-26",
                                        "--decisao", "aceito", "--confianca", "alta"])
        self.assertEqual(codigo, 0)
        self.assertEqual(json.loads(self.reg.read_text(encoding="utf-8"))["regra"], "PTC-26")


if __name__ == "__main__":
    unittest.main()
