"""Testes da checagem de preservação de sentido (PTC-22)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "ptc-br" / "scripts"))
import ptc_diff as pd  # noqa: E402

O_81 = ("Quando o certificado utilizado para a autenticação encontrar-se fora do seu período de validade, "
        "deverá ser realizado o procedimento de renovação para possibilitar a continuidade da operação.")
O_82 = ("O presente estudo objetiva proceder à comparação de metodologias estocásticas aplicadas à maximização "
        "do desempenho de configurações aeronáuticas sujeitas a alterações regulamentares.")
O_83 = "O sistema só aprova a assinatura quando o certificado é válido e não está revogado."


def altos(o, r):
    return {(a["classe"], a["tipo"]) for a in pd.comparar(o, r)["alertas"] if a["severidade"] == "alta"}


class ExemplosDaSpec(unittest.TestCase):
    def test_81_boa_sem_alerta_alto(self):
        r = "Se o certificado de autenticação estiver fora do período de validade, renove o certificado para continuar a operação."
        self.assertEqual(altos(O_81, r), set())

    def test_81_ruim_e_caso_do_judge(self):
        # "expirado" reduz o escopo, mas o diff não detecta: é responsabilidade do judge (Q3).
        r = "Se o certificado estiver expirado, renove o certificado. Depois, execute novamente a operação."
        res = pd.comparar(O_81, r)
        self.assertEqual(res["resumo"]["altos"], 0)
        self.assertIn("expirado", res["termos_novos"])

    def test_82_boa_sem_alerta(self):
        r = ("Este estudo compara métodos estocásticos usados para maximizar o desempenho de configurações "
             "de aeronaves sujeitas a alterações de regulamento.")
        self.assertEqual(altos(O_82, r), set())

    def test_82_ruim_numero_acrescentado(self):
        r = ("Este estudo compara três algoritmos de otimização estocástica usados no projeto de aeronaves. "
             "A comparação considera as mudanças nas regras da competição.")
        self.assertIn(("numero", "adicao"), altos(O_82, r))

    def test_83_boa_sem_alerta(self):
        r = "Somente se o certificado estiver válido e não estiver revogado, o sistema aprova a assinatura."
        self.assertEqual(altos(O_83, r), set())

    def test_83_ruim_perde_negacao_e_restricao(self):
        r = "O sistema aprova a assinatura quando o certificado é válido."
        self.assertEqual(altos(O_83, r), {("negacao", "perda"), ("restricao", "perda")})


class Classes(unittest.TestCase):
    def test_numero_perdido(self):
        self.assertIn(("numero", "perda"), altos("Aguarde 30 s.", "Aguarde."))

    def test_numero_com_unidade_igual(self):
        self.assertEqual(altos("Aplique 20 mV.", "Aplique uma tensão de 20 mV."), set())

    def test_alternativa_perdida(self):
        self.assertIn(("alternativa", "perda"), altos("Use o token ou a senha.", "Use o token e a senha."))

    def test_comparador_perdido(self):
        self.assertIn(("comparador", "perda"), altos("Use no mínimo 8 caracteres.", "Use 8 caracteres."))

    def test_enclise_nao_conta_como_condicao(self):
        r = pd.comparar("Quando o arquivo encontrar-se vazio, pare.", "Se o arquivo estiver vazio, pare.")
        self.assertFalse([a for a in r["alertas"] if a["classe"] == "condicao"])

    def test_sinonimos_de_restricao_se_compensam(self):
        self.assertEqual(altos("Só administradores acessam.", "Apenas administradores acessam."), set())

    def test_imperativo_substitui_obrigacao_sem_alerta_alto(self):
        self.assertEqual(altos("O usuário deve reiniciar o serviço.", "Reinicie o serviço."), set())


class Probabilidade(unittest.TestCase):
    def alertas(self, o, r):
        return [(a["tipo"], a["severidade"]) for a in pd.comparar(o, r)["alertas"] if a["classe"] == "probabilidade"]

    def test_mudanca_de_grau_e_alta(self):
        self.assertEqual(self.alertas("A falha é provável (55–80%).", "A falha é quase certa (95–99%)."),
                         [("perda", "alta")])

    def test_mesmo_grau_com_percentual_nao_alerta(self):
        self.assertEqual(altos("A causa provável (55–80%) é o certificado.",
                               "O certificado é a causa provável (55–80%)."), set())

    def test_percentual_da_escala_nao_conta_como_numero_novo(self):
        self.assertEqual(altos("A causa provável é o certificado.", "A causa provável (55–80%) é o certificado."), set())

    def test_vago_para_escala_pede_confirmacao(self):
        self.assertEqual(self.alertas("Talvez o lote atrase.", "O atraso do lote é provável (55–80%)."),
                         [("adicao", "media")])

    def test_grau_inventado_e_alto(self):
        self.assertEqual(self.alertas("O lote atrasa às sextas.", "O atraso do lote às sextas é provável (55–80%)."),
                         [("adicao", "alta")])


if __name__ == "__main__":
    unittest.main()
