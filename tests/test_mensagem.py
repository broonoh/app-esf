"""Testes para o módulo mensagem.py."""

from mensagem import (
    gerar_mensagem,
    gerar_mensagem_confirmacao,
    gerar_mensagem_personalizada,
)


# ============================================================
# DADOS BÁSICOS DA PESSOA
# ============================================================
class TestDadosBasicos:
    def test_inclui_nome(self):
        msg = gerar_mensagem({"nome": "João", "responsavel": ""}, "Igreja X")
        assert "João" in msg

    def test_inclui_responsavel(self):
        msg = gerar_mensagem(
            {"nome": "Maria", "responsavel": "Irmão Pedro"}, "Igreja X"
        )
        assert "Irmão Pedro" in msg

    def test_inclui_igreja(self):
        msg = gerar_mensagem({"nome": "Maria", "responsavel": ""}, "Igreja Central")
        assert "Igreja Central" in msg

    def test_campos_ausentes_no_dict_nao_quebra(self):
        # Usa .get com default, então não deve quebrar
        msg = gerar_mensagem({}, "Igreja X")
        assert "Olá, ! A Paz do Senhor Jesus!" in msg


# ============================================================
# BLOCO DE DOM
# ============================================================
class TestBlocoDom:
    def test_sem_dom_nao_adiciona_bloco(self):
        msg = gerar_mensagem({"nome": "A", "responsavel": ""}, "I")
        assert "dom espiritual" not in msg.lower()

    def test_com_dom(self):
        msg = gerar_mensagem(
            {"nome": "A", "responsavel": "", "dom": "Cura"}, "I"
        )
        assert "*Cura*" in msg
        assert "dom espiritual" in msg.lower()
        assert "experiência concedida por Deus" in msg
        assert "propósitos lindos" not in msg

    def test_dom_none_nao_quebra(self):
        msg = gerar_mensagem(
            {"nome": "A", "responsavel": "", "dom": None}, "I"
        )
        assert "dom espiritual" not in msg.lower()

    def test_dom_com_espacos_e_ignorado_se_vazio(self):
        msg = gerar_mensagem(
            {"nome": "A", "responsavel": "", "dom": "   "}, "I"
        )
        assert "dom espiritual" not in msg.lower()


# ============================================================
# COMBINAÇÕES
# ============================================================
class TestCombinacoes:
    def test_dom_e_dados_juntos(self):
        msg = gerar_mensagem(
            {"nome": "João", "responsavel": "Pedro", "dom": "Cura"},
            "Igreja X",
        )
        assert "João" in msg
        assert "Pedro" in msg
        assert "Igreja X" in msg
        assert "*Cura*" in msg

    def test_mensagem_nao_inclui_observacao(self):
        # A mensagem automática não deve mais trazer a observação da pessoa
        msg = gerar_mensagem(
            {"nome": "A", "responsavel": "", "observacao": "Pediu oração"}, "I"
        )
        assert "Pediu oração" not in msg
        assert "Observação" not in msg

    def test_mensagem_termina_com_saudacao(self):
        msg = gerar_mensagem({"nome": "A", "responsavel": ""}, "I")
        assert msg.strip().endswith("Deus abençoe!")


# ============================================================
# MENSAGEM PERSONALIZADA (MODELO CADASTRADO)
# ============================================================
class TestMensagemPersonalizada:
    def test_substitui_placeholders(self):
        corpo = "Olá, {nome}! Aqui é {responsavel}, da {igreja}."
        msg = gerar_mensagem_personalizada(
            {"nome": "Ana", "responsavel": "Carlos"}, "Igreja X", corpo
        )
        assert "Olá, Ana! Aqui é Carlos, da Igreja X." == msg

    def test_igreja_vazia_nao_quebra(self):
        corpo = "Da {igreja}."
        msg = gerar_mensagem_personalizada(
            {"nome": "Ana", "responsavel": ""}, "", corpo
        )
        assert "Da ." in msg

    def test_corpo_vazio(self):
        msg = gerar_mensagem_personalizada({"nome": "A"}, "I", "")
        assert msg == ""


# ============================================================
# MENSAGEM DE CONFIRMAÇÃO DE VISITA
# ============================================================
class TestMensagemConfirmacao:
    def test_inclui_nome_e_data(self):
        msg = gerar_mensagem_confirmacao("João", "15/03/2026")
        assert "João" in msg
        assert "15/03/2026" in msg

    def test_inclui_hora_quando_informada(self):
        msg = gerar_mensagem_confirmacao("João", "15/03/2026", "14:30")
        assert "15/03/2026 às 14:30" in msg

    def test_sem_hora_nao_quebra(self):
        msg = gerar_mensagem_confirmacao("João", "15/03/2026", "")
        assert "às" not in msg
