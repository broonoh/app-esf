"""
conftest.py — Configuração compartilhada dos testes.

Cria um banco SQLite temporário em memória/arquivo para cada teste,
isolando completamente o banco real.
"""

import os
import sys
import tempfile

import pytest

# Garante que os módulos do projeto sejam encontrados
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Redireciona o DB para um arquivo temporário ANTES de importar db
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["FLET_APP_STORAGE_DATA"] = os.path.dirname(_tmp_db.name)

import db  # noqa: E402
db.DB_PATH = _tmp_db.name


@pytest.fixture(autouse=True)
def banco_limpo():
    """Garante um banco limpo antes de cada teste."""
    if os.path.exists(_tmp_db.name):
        os.remove(_tmp_db.name)
    db.DB_PATH = _tmp_db.name
    db.init_db()
    yield
    if os.path.exists(_tmp_db.name):
        os.remove(_tmp_db.name)


@pytest.fixture
def sample_pessoa():
    """Fixture: cadastra uma pessoa e retorna o id."""
    return db.inserir(
        "pessoas",
        {"nome": "Maria Teste", "telefone": "11999999999", "endereco": "Rua X"},
    )


@pytest.fixture
def sample_igreja():
    """Fixture: cadastra uma igreja e retorna o id."""
    return db.inserir("igrejas", {"nome": "Igreja Teste"})


@pytest.fixture
def sample_mensagem():
    """Fixture: cadastra um modelo de mensagem e retorna o id."""
    return db.inserir(
        "mensagens",
        {
            "titulo": "Modelo padrão",
            "corpo": "Olá, {nome}! Aqui é {responsavel}, da {igreja}.",
        },
    )