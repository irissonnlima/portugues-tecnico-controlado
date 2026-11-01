"""Testes do verificador determinístico. Rode: python3 -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "ptc-br" / "scripts"))
import ptc_check as pc  # noqa: E402


def regras(texto, perfil="T"):
    return [a["regra"] for a in pc.verificar(texto, perfil)["achados"]]


class Contagem(unittest.TestCase):
    """Seção 5 da spec."""

    def test_palavras_simples(self):
        self.assertEqual(pc.contar_palavras("Renove o certificado."), 3)

    def test_hifen_e_enclise(self):
        self.assertEqual(pc.contar_palavras("Renove-o com o guarda-chuva."), 4)

    def test_numero_com_unidade(self):
        self.assertEqual(pc.contar_palavras("Aplique 20 mV por 1,5 s."), 4)

    def test_identificador_de_norma(self):
        self.assertEqual(pc.contar_palavras("Siga a ABNT NBR ISO 24495-1 agora."), 4)

    def test_codigo_e_url(self):
        txt = pc.limpar_inline("Rode `kubectl get pods -A` e abra https://exemplo.com/a/b.")
        self.assertEqual(pc.contar_palavras(txt), 5)

    def test_pontuacao_isolada_nao_conta(self):
        self.assertEqual(pc.contar_palavras("Abra o arquivo — depois feche."), 5)


class Frases(unittest.TestCase):
    def test_abreviacao_nao_divide(self):
        self.assertEqual(len(pc.dividir_frases("Use um formato, p. ex. JSON. Depois salve.")), 2)

    def test_decimal_e_versao_nao_dividem(self):
        self.assertEqual(len(pc.dividir_frases("Instale a v2.1.0 com 1.5 GB livres. Reinicie.")), 2)


class Regras(unittest.TestCase):
    def test_ptc03_passo_longo(self):
        passo = "1. " + " ".join(["palavra"] * 21) + "."
        self.assertIn("PTC-03", regras(passo))

    def test_ptc03_limite_exato_passa(self):
        passo = "1. Abra " + " ".join(["palavra"] * 19) + "."
        self.assertNotIn("PTC-03", regras(passo))

    def test_ptc04_descricao_longa(self):
        self.assertIn("PTC-04", regras(" ".join(["palavra"] * 26) + "."))

    def test_ptc11_nominalizacao(self):
        self.assertIn("PTC-11", regras("Realize a verificação do arquivo."))

    def test_ptc11_locucao_fixa(self):
        self.assertIn("PTC-11", regras("O time vai fazer uso de filas."))

    def test_ptc11_nao_marca_execute_os_testes(self):
        self.assertNotIn("PTC-11", regras("Execute os testes antes do merge."))

    def test_ptc12_vaga(self):
        self.assertIn("PTC-12", regras("Responda rapidamente ao alerta."))

    def test_ptc05_passiva_com_agente(self):
        r = pc.verificar("O arquivo é validado pelo sistema.")["achados"]
        self.assertTrue(any(a["regra"] == "PTC-05" and a["confianca"] == "media" for a in r))

    def test_ptc05_ignora_muito(self):
        self.assertNotIn("PTC-05", regras("A falha é muito rara."))

    def test_ptc05_ignora_adjetivo(self):
        self.assertNotIn("PTC-05", regras("O valor é adequado para o teste."))

    def test_ptc15_paragrafo_longo(self):
        self.assertIn("PTC-15", regras(" ".join(["Abra o arquivo."] * 7)))

    def test_ptc17_sigla_sem_definicao(self):
        self.assertIn("PTC-17", regras("O ERP grava os pedidos."))

    def test_ptc17_sigla_definida(self):
        self.assertNotIn("PTC-17", regras("O Planejamento de Recursos (ERP) grava os pedidos. O ERP responde."))

    def test_ptc17_sigla_declarada(self):
        self.assertNotIn("PTC-17", regras("<!-- ptc-siglas: ERP -->\nO ERP grava os pedidos."))

    def test_ptc18_infinitivo_em_passo(self):
        self.assertIn("PTC-18", regras("1. Selecionar o arquivo."))

    def test_ptc18_imperativo_passa(self):
        self.assertNotIn("PTC-18", regras("1. Selecione o arquivo."))

    def test_ptc21_aviso_vazio(self):
        self.assertIn("PTC-21", regras("> **Atenção:** confira o arquivo."))

    def test_ptc21_aviso_com_consequencia(self):
        self.assertNotIn("PTC-21", regras("> **Atenção:** não desligue o servidor: a base pode corromper."))

    def test_ptc23_negacoes(self):
        self.assertIn("PTC-23", regras("Não é possível não validar sem token."))

    def test_excecao_suprime_regra(self):
        txt = "<!-- ptc-excecao: PTC-03; motivo: parâmetro longo -->\n1. " + " ".join(["palavra"] * 22) + "."
        res = pc.verificar(txt)
        self.assertNotIn("PTC-03", [a["regra"] for a in res["achados"]])
        self.assertEqual(res["excecoes_aplicadas"][0]["regra"], "PTC-03")

    def test_excecao_sem_motivo(self):
        self.assertIn("PTC-24", regras("<!-- ptc-excecao: PTC-03 -->\n1. Abra."))

    def test_codigo_e_titulo_ignorados(self):
        txt = "# Realize a verificação do ERP\n\n```\nrealize a verificação\n```\n"
        self.assertEqual(regras(txt), [])


class PrecisaoCorpus(unittest.TestCase):
    """Falsos positivos encontrados no corpus real (0.2.0)."""

    def conf(self, texto, regra):
        return [a["confianca"] for a in pc.verificar(texto)["achados"] if a["regra"] == regra]

    def test_concordancia_negativa_nao_conta(self):
        for f in ["Não há fallback nem cache.", "Então não precisa de mais nada.", "Nunca use X nem Y como chave."]:
            self.assertEqual(self.conf(f, "PTC-23"), [], f)

    def test_oracoes_coordenadas_nao_somam(self):
        self.assertEqual(self.conf("O DNS não resolve e os IPs não têm rota.", "PTC-23"), [])

    def test_negacao_dupla_e_baixa(self):
        self.assertEqual(self.conf("Nunca entregue tabela sem índice.", "PTC-23"), ["baixa"])

    def test_dois_nao_na_oracao_e_media(self):
        self.assertEqual(self.conf("Não é possível não validar o token.", "PTC-23"), ["media"])

    def test_nome_de_arquivo_nao_e_sigla(self):
        self.assertEqual(self.conf("Edite o SKILL.md e o README.md.", "PTC-17"), [])

    def test_caixa_alta_de_enfase_e_baixa(self):
        self.assertEqual(self.conf("Antes de editar, LEIA o guia.", "PTC-17"), ["baixa"])

    def test_siglas_extra_pela_cli(self):
        res = pc.verificar("O DDL cria a tabela em HML.", siglas_extra={"DDL", "HML"})
        self.assertNotIn("PTC-17", [a["regra"] for a in res["achados"]])

    def test_quantificador_vago_e_baixa(self):
        self.assertEqual(self.conf("Várias tabelas têm índice.", "PTC-12"), ["baixa"])

    def test_passo_com_substantivo_em_or_nao_e_infinitivo(self):
        self.assertEqual(self.conf("1. Valor sensível nunca vai para o repositório.", "PTC-18"), [])

    def test_levar_correcao_nao_e_nominalizacao(self):
        self.assertEqual(self.conf("O back-merge leva a correção para HML.", "PTC-11"), [])


class Perfis(unittest.TestCase):
    def test_perfil_L_nao_aplica_ptc04(self):
        self.assertNotIn("PTC-04", regras(" ".join(["palavra"] * 26) + ".", "L"))

    def test_perfil_C_torna_ptc11_obrigatoria(self):
        r = pc.verificar("Realize a verificação do arquivo.", "C")["achados"]
        self.assertEqual([a["nivel"] for a in r if a["regra"] == "PTC-11"], ["O"])

    def test_exemplos_da_spec_nao_quebram(self):
        spec = (Path(pc.__file__).resolve().parents[1] / "references" / "regras.md").read_text(encoding="utf-8")
        res = pc.verificar(spec)
        self.assertGreater(res["blocos_verificados"], 50)


if __name__ == "__main__":
    unittest.main()


class Diretivas(unittest.TestCase):
    """0.4.0: ptc-ignorar, ptc-idioma, ptc-mencoes e detecção automática de inglês."""

    def test_ignorar_proximo_bloco(self):
        res = pc.verificar("<!-- ptc-ignorar: exemplo incorreto -->\nRealize a verificação.\n\nRealize a análise.")
        self.assertEqual(len([a for a in res["achados"] if a["regra"] == "PTC-11"]), 1)
        self.assertEqual(res["blocos_ignorados"][0]["motivo"], "ignorar: exemplo incorreto")

    def test_regiao_ignorada(self):
        txt = "<!-- ptc-ignorar-inicio: exemplos -->\nRealize a verificação.\n\nUtilize o token.\n<!-- ptc-ignorar-fim -->\n\nRealize a análise."
        res = pc.verificar(txt)
        self.assertEqual([a["linha"] for a in res["achados"]], [7])

    def test_idioma_marcado_usa_perfil_ste(self):
        res = pc.verificar("<!-- ptc-idioma: en -->\nExecute os testes rapidamente.")
        self.assertEqual(res["blocos_ingles_ste"], 1)
        self.assertFalse([a for a in res["achados"] if a["regra"] == "PTC-12"])   # regra do português não vale

    def test_outro_idioma_marcado_fica_fora(self):
        res = pc.verificar("<!-- ptc-idioma: es -->\nUtilice el token rápidamente.")
        self.assertEqual(res["achados"], [])
        self.assertEqual(res["blocos_ignorados"][0]["motivo"], "idioma: es")

    def test_ingles_detectado_usa_perfil_ste(self):
        res = pc.verificar("Execute the query and check the results quickly.")
        self.assertEqual(res["blocos_ingles_ste"], 1)
        self.assertEqual(res["blocos_ignorados"], [])

    def test_ingles_pode_ser_ignorado(self):
        res = pc.verificar("Utilize the token and check the results.", ingles="ignorar")
        self.assertEqual(res["achados"], [])
        self.assertEqual(res["blocos_ignorados"][0]["motivo"], "idioma: en")

    def test_termos_ingleses_em_frase_portuguesa_nao_e_ingles(self):
        self.assertFalse(pc.parece_ingles("Faça o commit da branch e abra o pull request."))

    def test_deteccao_desligada(self):
        res = pc.verificar("Execute the query and check the results.", detectar_idioma=False)
        self.assertEqual(res["blocos_ingles_ste"], 0)

    def test_mencoes_em_italico(self):
        txt = "<!-- ptc-mencoes: italico -->\nNão use *utilizar* nem *a nível de*. Utilize o verbo usar."
        msgs = [a["mensagem"] for a in pc.verificar(txt)["achados"]]
        self.assertEqual(len([m for m in msgs if "V-0100" in m]), 1)
        self.assertFalse([m for m in msgs if "V-0210" in m])

    def test_mencao_conta_como_uma_palavra(self):
        self.assertEqual(pc.contar_palavras(pc.mascarar_mencoes("Use *dar início a* aqui.", {"italico"})), 3)


class PrecisaoDocumentacao(unittest.TestCase):
    """Falsos positivos achados ao aplicar o PTC-BR na própria documentação (0.4.0)."""

    def regras(self, texto):
        return [a["regra"] for a in pc.verificar(texto)["achados"]]

    def test_sigla_definida_no_titulo(self):
        self.assertNotIn("PTC-17", self.regras("# PTC-BR — Português Técnico Controlado\n\nO PTC-BR define regras."))
        self.assertNotIn("PTC-17", self.regras("# Planejamento de Recursos (ERP)\n\nO ERP grava pedidos."))

    def test_sigla_com_sufixo_definida(self):
        self.assertNotIn("PTC-17", self.regras("O PTC-BR (Português Técnico Controlado) define regras. O PTC-T é o perfil."))

    def test_marcador_de_posicao_nao_e_sigla(self):
        self.assertNotIn("PTC-17", self.regras("Cite o ID da regra (PTC-NN)."))

    def test_execute_a_aplicacao(self):
        self.assertNotIn("PTC-11", self.regras("Execute a aplicação com o perfil de teste."))

    def test_adjetivo_proparoxitono_nao_e_passiva(self):
        self.assertNotIn("PTC-05", self.regras("O certificado é válido."))
        self.assertIn("PTC-05", self.regras("O arquivo foi incluído pelo sistema."))


class PerfilSTE(unittest.TestCase):
    """Blocos em inglês: núcleo do ASD-STE100. Regras próprias do português não valem."""

    def achados(self, texto):
        return pc.verificar(texto)["achados"]

    def msgs(self, texto, regra):
        return [a["mensagem"] for a in self.achados(texto) if a["regra"] == regra]

    def test_passo_longo(self):
        passo = "1. Open the " + " ".join(["file"] * 20) + " now."
        self.assertTrue(self.msgs(passo, "PTC-03"))

    def test_voz_passiva_com_agente(self):
        r = [a for a in self.achados("The file is validated by the system.") if a["regra"] == "PTC-05"]
        self.assertEqual(r[0]["confianca"], "media")
        self.assertIn("[EN · STE]", r[0]["mensagem"])

    def test_passiva_irregular(self):
        self.assertTrue(self.msgs("The report was written by the team.", "PTC-05"))

    def test_imperativo_no_passo(self):
        self.assertTrue(self.msgs("1. You should open the file in the editor.", "PTC-18"))
        self.assertTrue(self.msgs("1. Opening the file in the editor is the first step.", "PTC-18"))
        self.assertEqual(self.msgs("1. Open the file in the editor.", "PTC-18"), [])

    def test_vocabulario_nao_preferido(self):
        self.assertTrue(any("utilize" in m for m in self.msgs("Utilize the token to access the API.", "PTC-25")))
        self.assertTrue(any("in order to" in m for m in self.msgs("Restart the service in order to apply it.", "PTC-25")))

    def test_forma_ing_baixa_e_excecoes(self):
        r = [a for a in self.achados("The service keeps retrying the request.") if "-ing" in a["mensagem"]]
        self.assertEqual([a["confianca"] for a in r], ["baixa"])
        self.assertFalse([a for a in self.achados("The string is empty during the test.") if "-ing" in a["mensagem"]])

    def test_aviso_sem_consequencia(self):
        self.assertTrue(self.msgs("> **Warning:** check the file.", "PTC-21"))
        self.assertEqual(self.msgs("> **Warning:** do not stop the server: the database can become corrupt.", "PTC-21"), [])

    def test_genero_nao_vale_em_ingles(self):
        doc = "The pipeline runs every night.\n\nThe query returns the issues and the results.\n\nNo issues found."
        self.assertEqual(self.msgs(doc, "PTC-08"), [])

    def test_frase_curta_segue_a_maioria_do_documento(self):
        doc = ("The service reads the queue and writes the result to the database.\n\n"
               "If the queue is empty, the service waits for the next message.\n\n- No issues found")
        res = pc.verificar(doc)
        self.assertEqual(res["blocos_ingles_ste"], 3)

    def test_frase_curta_em_documento_portugues_continua_portugues(self):
        doc = "O serviço lê a fila e grava o resultado no banco.\n\n- Pipeline OK"
        self.assertEqual(pc.verificar(doc)["blocos_ingles_ste"], 0)

    def test_regras_do_portugues_nao_valem(self):
        r = {a["regra"] for a in self.achados("The causa provável is the certificate and the result arrives quickly.")}
        self.assertNotIn("PTC-26", r)
        self.assertNotIn("PTC-12", r)


class IngAceitos(unittest.TestCase):
    """0.5.1: substantivos técnicos em -ing aceitos na lista geral e na camada do time."""

    def ing(self, texto, **kw):
        return [a["mensagem"] for a in pc.verificar(texto, **kw)["achados"] if "-ing" in a["mensagem"]]

    def test_lista_geral(self):
        self.assertEqual(self.ing("The service uses connection pooling and request tracing."), [])

    def test_camada_do_time(self):
        txt = "The job runs the backfilling of the table."
        self.assertTrue(self.ing(txt))
        self.assertEqual(self.ing(txt, ing_aceitos={"backfilling"}), [])

    def test_camada_exemplo_carrega_ing_aceitos(self):
        cc = pc.carregar_camadas_completo([str(Path(pc.__file__).resolve().parents[3] / "exemplos" / "camada-time.yaml")])
        self.assertIn("backfilling", cc["ing_aceitos"])

    def test_camada_ingles_invalida(self):
        import json, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"ingles": {"outra_chave": []}}, f)
        with self.assertRaisesRegex(ValueError, "ing_aceitos"):
            pc.carregar_camadas_completo([f.name])
