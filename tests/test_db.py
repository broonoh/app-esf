"""Testes para o módulo db.py."""

import os

import pytest

import db


# ============================================================
# SCHEMA / INIT
# ============================================================
class TestInitDb:
    def test_tabelas_criadas(self):
        with db.conectar() as conn:
            tabelas = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        esperadas = {
            "igrejas", "pessoas", "mensagens", "assistidos",
            "grupos_assistencia", "grupo_auxiliares",
            "mensagem_gerada", "visita_realizada",
        }
        assert esperadas.issubset(tabelas)

    def test_init_idempotente(self):
        """Rodar init_db duas vezes não deve quebrar."""
        db.init_db()
        db.init_db()


# ============================================================
# GRUPOS DE ASSISTÊNCIA (CRUD livre: cadastrar/editar/excluir)
# ============================================================
class TestGruposAssistencia:
    def test_criado_vazio_por_padrao(self):
        assert db.listar("grupos_assistencia") == []

    def test_inserir_e_listar(self):
        gid = db.inserir("grupos_assistencia", {"grupo": "1"})
        grupos = db.listar("grupos_assistencia")
        assert len(grupos) == 1
        assert grupos[0]["id"] == gid
        assert grupos[0]["grupo"] == "1"
        assert grupos[0]["responsavel"] == ""

    def test_grupo_duplicado_levanta_integrity_error(self):
        db.inserir("grupos_assistencia", {"grupo": "1"})
        with pytest.raises(Exception):
            db.inserir("grupos_assistencia", {"grupo": "1"})

    def test_atualizar_responsavel(self):
        gid = db.inserir("grupos_assistencia", {"grupo": "1"})
        db.atualizar("grupos_assistencia", gid, {"responsavel": "Ari"})
        atualizado = next(
            g for g in db.listar("grupos_assistencia") if g["id"] == gid
        )
        assert atualizado["responsavel"] == "Ari"

    def test_excluir(self):
        gid = db.inserir("grupos_assistencia", {"grupo": "1"})
        db.excluir("grupos_assistencia", gid)
        assert db.listar("grupos_assistencia") == []


# ============================================================
# AUXILIARES DO GRUPO (registros independentes)
# ============================================================
class TestGrupoAuxiliares:
    def test_inserir_e_listar(self):
        gid = db.inserir("grupos_assistencia", {"grupo": "1"})
        aid = db.inserir("grupo_auxiliares", {"grupo_id": gid, "nome": "Bruno"})
        auxiliares = db.listar("grupo_auxiliares")
        assert len(auxiliares) == 1
        assert auxiliares[0]["id"] == aid
        assert auxiliares[0]["grupo_id"] == gid
        assert auxiliares[0]["nome"] == "Bruno"

    def test_varios_auxiliares_no_mesmo_grupo(self):
        gid = db.inserir("grupos_assistencia", {"grupo": "1"})
        db.inserir("grupo_auxiliares", {"grupo_id": gid, "nome": "Bruno"})
        db.inserir("grupo_auxiliares", {"grupo_id": gid, "nome": "Carla"})
        nomes = {a["nome"] for a in db.listar("grupo_auxiliares")}
        assert nomes == {"Bruno", "Carla"}

    def test_excluir_auxiliar(self):
        gid = db.inserir("grupos_assistencia", {"grupo": "1"})
        aid = db.inserir("grupo_auxiliares", {"grupo_id": gid, "nome": "Bruno"})
        db.excluir("grupo_auxiliares", aid)
        assert db.listar("grupo_auxiliares") == []

    def test_excluir_grupo_cascateia_auxiliares(self):
        gid = db.inserir("grupos_assistencia", {"grupo": "1"})
        db.inserir("grupo_auxiliares", {"grupo_id": gid, "nome": "Bruno"})
        db.excluir("grupos_assistencia", gid)
        assert db.listar("grupo_auxiliares") == []


# ============================================================
# CRUD GENÉRICO
# ============================================================
class TestCrudGenerico:
    def test_inserir_e_listar(self):
        db.inserir("igrejas", {"nome": "Igreja A"})
        db.inserir("igrejas", {"nome": "Igreja B"})
        igrejas = db.listar("igrejas")
        assert len(igrejas) == 2
        # listar() ordena por id DESC
        assert igrejas[0]["nome"] == "Igreja B"

    def test_atualizar(self):
        ig_id = db.inserir("igrejas", {"nome": "Antiga"})
        db.atualizar("igrejas", ig_id, {"nome": "Nova"})
        igrejas = db.listar("igrejas")
        assert igrejas[0]["nome"] == "Nova"

    def test_excluir(self):
        ig_id = db.inserir("igrejas", {"nome": "Vai sair"})
        db.excluir("igrejas", ig_id)
        assert db.listar("igrejas") == []

    def test_nome_duplicado_levanta_integrity_error(self):
        db.inserir("igrejas", {"nome": "Única"})
        with pytest.raises(Exception):
            db.inserir("igrejas", {"nome": "Única"})


# ============================================================
# DOM / OBSERVAÇÃO COMO TEXTO LIVRE NA PESSOA
# ============================================================
class TestDomObservacaoPessoa:
    def test_pessoa_guarda_dom_e_observacao(self):
        pid = db.inserir(
            "pessoas",
            {
                "nome": "Carlos",
                "telefone": "",
                "endereco": "",
                "dom": "Cura e Profecia",
                "observacao": "Pediu oração pela família",
            },
        )
        pessoa = db.listar("pessoas")[0]
        assert pessoa["id"] == pid
        assert pessoa["dom"] == "Cura e Profecia"
        assert pessoa["observacao"] == "Pediu oração pela família"

    def test_atualizar_dom_e_observacao(self, sample_pessoa):
        db.atualizar(
            "pessoas", sample_pessoa, {"dom": "Ensino", "observacao": "Aberta a visita"}
        )
        pessoa = next(p for p in db.listar("pessoas") if p["id"] == sample_pessoa)
        assert pessoa["dom"] == "Ensino"
        assert pessoa["observacao"] == "Aberta a visita"

    def test_dom_e_observacao_vazios_por_padrao(self, sample_pessoa):
        pessoa = next(p for p in db.listar("pessoas") if p["id"] == sample_pessoa)
        assert pessoa["dom"] == ""
        assert pessoa["observacao"] == ""


# ============================================================
# CONSULTA COM JOIN
# ============================================================
class TestListarAssistidosCompletos:
    def test_join_traz_dados_relacionados(
        self, sample_pessoa, sample_igreja, sample_mensagem
    ):
        db.inserir(
            "assistidos",
            {
                "pessoa_id": sample_pessoa,
                "igreja_id": sample_igreja,
                "responsavel": "Resp X",
                "grupo": "2",
                "status": "Aceitou",
                "data_agendada": "",
                "mensagem_id": sample_mensagem,
            },
        )
        assistidos = db.listar_assistidos_completos()
        assert len(assistidos) == 1
        a = assistidos[0]
        assert a["nome"] == "Maria Teste"
        assert a["igreja_nome"] == "Igreja Teste"
        assert a["mensagem_titulo"] == "Modelo padrão"

    def test_assistido_sem_igreja_e_mensagem(self, sample_pessoa):
        db.inserir(
            "assistidos",
            {
                "pessoa_id": sample_pessoa,
                "igreja_id": None,
                "responsavel": "",
                "grupo": "1",
                "status": "Aceitou",
                "data_agendada": "",
                "mensagem_id": None,
            },
        )
        a = db.listar_assistidos_completos()[0]
        assert a["igreja_nome"] is None
        assert a["mensagem_titulo"] is None


# ============================================================
# OBTER (CRUD genérico: registro único por id)
# ============================================================
class TestObter:
    def test_obter_registro_existente(self, sample_pessoa):
        pessoa = db.obter("pessoas", sample_pessoa)
        assert pessoa is not None
        assert pessoa["id"] == sample_pessoa

    def test_obter_registro_inexistente(self):
        assert db.obter("pessoas", 999999) is None


# ============================================================
# VISITA REALIZADA (histórico permanente)
# ============================================================
class TestVisitaRealizada:
    def test_registrar_e_listar(self, sample_pessoa):
        db.registrar_visita_realizada(
            sample_pessoa, "Maria Teste", "15/03/2026", "14:30", "1", "Ari"
        )
        visitas = db.listar("visita_realizada")
        assert len(visitas) == 1
        assert visitas[0]["nome"] == "Maria Teste"
        assert visitas[0]["data_realizada"] == "15/03/2026"

    def test_permanece_apos_excluir_agendamento(self, sample_pessoa):
        aid = db.inserir(
            "assistidos",
            {
                "pessoa_id": sample_pessoa,
                "igreja_id": None,
                "responsavel": "",
                "grupo": "1",
                "status": "Aceitou",
                "data_agendada": "",
                "mensagem_id": None,
            },
        )
        db.registrar_visita_realizada(
            sample_pessoa, "Maria Teste", "15/03/2026", "14:30", "1", "Ari"
        )
        db.excluir("assistidos", aid)
        assert len(db.listar("visita_realizada")) == 1