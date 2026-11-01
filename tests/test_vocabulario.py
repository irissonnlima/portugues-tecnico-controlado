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
            if (v["status"] == "aprovado" and not v.get("probabilidade")) or v.get("sentidos"):
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
        conf = {a["mensagem"].split("(")[-1].rstrip(").").split(",")[0]: (a["nivel"], a["confianca"])
                for a in achados("Utilize o token. A nível de servidor, confira o log.")}
        self.assertEqual(conf["V-0100"], ("R", "media"))   # não preferido
        self.assertEqual(conf["V-0210"], ("O", "alta"))    # proibido: obrigatória em qualquer perfil
        self.assertNotIn("V-0114", conf)                   # conferir: sinônimo aceito (decisão 0.3.0)

    def test_o_mesmo_adjetivo_nao_dispara(self):
        self.assertEqual(achados("Use o mesmo nome nos dois ambientes.", "PTC-07"), [])

    def test_o_mesmo_predicativo_nao_dispara(self):
        self.assertEqual(achados("O contrato é sempre o mesmo.", "PTC-07"), [])

    def test_se_encontrar_condicional_nao_dispara(self):
        self.assertFalse([a for a in achados("Se encontrar esse valor, pergunte antes.") if "V-0118" in a["mensagem"]])

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


CAMADA = RAIZ / "exemplos" / "camada-time.yaml"


@unittest.skipIf(cv is None, "PyYAML ausente")
class Camadas(unittest.TestCase):
    def setUp(self):
        self.vocab, self.siglas, self.nomes = pc.carregar_camadas([str(CAMADA)])

    def ids(self, texto):
        res = pc.verificar(texto, siglas_extra=self.siglas, vocabulario=self.vocab, camadas=self.nomes)
        return {a["mensagem"].split("(")[-1].split(",")[0].rstrip(").") for a in res["achados"]}

    def test_sem_camada_verificar_e_conferir_sao_aceitos(self):
        self.assertEqual({a["regra"] for a in achados("Verifique o log. Confira o log.")}, set())

    def test_camada_sobrepoe_verbete_geral(self):
        self.assertIn("V-0001", self.ids("Verifique o log."))
        self.assertNotIn("V-0114", self.ids("Confira o log."))

    def test_camada_acrescenta_verbete(self):
        self.assertIn("T-0001", self.ids("Abra o dashboard."))

    def test_camada_traz_siglas(self):
        res = pc.verificar("O ETL grava no DW.", siglas_extra=self.siglas, vocabulario=self.vocab)
        self.assertNotIn("PTC-17", [a["regra"] for a in res["achados"]])

    def test_mensagem_cita_a_camada(self):
        res = pc.verificar("Verifique o log.", vocabulario=self.vocab)
        self.assertIn("camada time-exemplo", res["achados"][0]["mensagem"])

    def test_camada_json_sem_pyyaml(self):
        import json, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"nome": "j", "sobrepor": [{"lema": "usar", "status": "proibido", "preferir": ["empregar"]}]}, f)
        vocab, _, _ = pc.carregar_camadas([f.name])
        r = pc.verificar("Use o token.", vocabulario=vocab)["achados"]
        self.assertEqual([(a["nivel"], a["confianca"]) for a in r], [("O", "alta")])

    def test_ultima_camada_vence(self):
        import json, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"nome": "volta", "sobrepor": [{"id": "V-0001", "status": "aprovado"}]}, f)
        vocab, _, _ = pc.carregar_camadas([str(CAMADA), f.name])
        self.assertEqual(pc.verificar("Verifique o log.", vocabulario=vocab)["achados"], [])

    def test_camada_invalida_falha_com_mensagem(self):
        import json, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"sobrepor": [{"id": "V-9999", "status": "aprovado"}]}, f)
        with self.assertRaisesRegex(ValueError, "não encontrado: V-9999"):
            pc.carregar_camadas([f.name])

    def test_cli_codigo_2_para_camada_invalida(self):
        r = subprocess.run([sys.executable, str(RAIZ / "skills/ptc-br/scripts/ptc_check.py"), "--texto", "x",
                            "--vocabulario", "/nao/existe.yaml"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


try:
    LEM = pc.criar_lematizador()
except ImportError:
    LEM = None


@unittest.skipIf(LEM is None, "simplemma ausente (opcional)")
class Lematizacao(unittest.TestCase):
    def ids(self, texto):
        return [a["mensagem"] for a in pc.verificar(texto, lematizar=LEM)["achados"] if a["regra"] == "PTC-25"]

    def test_acha_forma_que_a_flexao_nao_gera(self):
        self.assertTrue(any("V-0100" in m and "por lema" in m for m in self.ids("Nós utilizaremos o token.")))

    def test_nao_duplica_o_que_a_regex_achou(self):
        self.assertEqual(len([m for m in self.ids("Utilize o token.") if "V-0100" in m]), 1)

    def test_respeita_formas_explicitas(self):
        self.assertFalse([m for m in self.ids("Crie uma tabela auxiliar.") if "V-0108" in m])

    def test_sem_lematizar_nao_acha(self):
        self.assertFalse([a for a in pc.verificar("Nós utilizaremos o token.")["achados"] if "V-0100" in a["mensagem"]])


class Probabilidade(unittest.TestCase):
    """PTC-26: termo da escala exige percentual entre parênteses, e o número precisa caber na faixa."""

    def msgs(self, texto):
        return [a["mensagem"] for a in pc.verificar(texto)["achados"] if a["regra"] == "PTC-26"]

    def test_sem_percentual(self):
        self.assertTrue(any("sem percentual" in m for m in self.msgs("A causa provável é o certificado.")))

    def test_faixa_coerente_passa(self):
        for f in ["A causa provável (55–80%) é o certificado.", "É provável (70%) que atrase.",
                  "É provável (60% a 75%) que atrase.", "É provável (~70%) que atrase.",
                  "É provável (70,5 %) que atrase.", "O lote quase certamente (95–99%) termina."]:
            self.assertEqual(self.msgs(f), [], f)

    def test_faixa_incoerente(self):
        m = self.msgs("A falha é muito provável (60%).")
        self.assertTrue(any("incoerente" in x for x in m))
        r = [a for a in pc.verificar("A falha é muito provável (60%).")["achados"] if a["regra"] == "PTC-26"]
        self.assertIn("provável (55–80%)", r[0]["sugestao"])

    def test_faixa_que_ultrapassa_o_termo(self):
        self.assertTrue(self.msgs("O atraso é provável (50–90%)."))

    def test_termo_aninhado_conta_uma_vez(self):
        m = self.msgs("O pico é muito provável (85%).")
        self.assertEqual(m, [])

    def test_improvavel_nao_e_provavel(self):
        self.assertEqual(self.msgs("O erro é improvável (30%)."), [])

    def test_vagos(self):
        for f in ["Talvez volte amanhã.", "É possível que atrase.", "O token certamente expira.", "Há grande chance de pico."]:
            self.assertTrue(self.msgs(f), f)

    def test_capacidade_nao_e_probabilidade(self):
        self.assertEqual(self.msgs("É possível exportar em CSV."), [])

    def test_nivel_por_perfil(self):
        r = [a for a in pc.verificar("A causa provável é X.", "L")["achados"] if a["regra"] == "PTC-26"]
        self.assertEqual(r[0]["nivel"], "R")
        r = [a for a in pc.verificar("A causa provável é X.", "T")["achados"] if a["regra"] == "PTC-26"]
        self.assertEqual(r[0]["nivel"], "O")


class GeneroDoGlossario(unittest.TestCase):
    def ptc08(self, texto):
        return [a["mensagem"] for a in pc.verificar(texto)["achados"] if a["regra"] == "PTC-08"]

    def test_genero_oposto(self):
        self.assertTrue(self.ptc08("Rode a pipeline de novo."))
        self.assertTrue(self.ptc08("O query falhou."))

    def test_genero_certo_e_plural(self):
        self.assertEqual(self.ptc08("Rode o pipeline. Revise os commits e as branches."), [])

    def test_preposicao_ao_nao_e_artigo_feminino(self):
        self.assertEqual(self.ptc08("Aplique a correção ao deploy."), [])

    def test_substantivo_ingles_aprovado_nao_gera_ptc25(self):
        self.assertFalse([a for a in pc.verificar("Faça o commit e o deploy.")["achados"] if a["regra"] == "PTC-25"])


class PrecisaoCorpus040(unittest.TestCase):
    def test_palavra_chave_sql_nao_e_verbo(self):
        self.assertFalse([a for a in pc.verificar("O cliente bloqueia INSERT/UPDATE/DELETE.")["achados"]
                          if "V-0808" in a["mensagem"]])

    def test_ingles_com_do_not(self):
        self.assertTrue(pc.parece_ingles("Do not delete files."))

    def test_release_sem_genero(self):
        self.assertFalse([a for a in pc.verificar("O release fica instalado.")["achados"] if a["regra"] == "PTC-08"])
