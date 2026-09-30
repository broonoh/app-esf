"""
db.py — Camada de acesso ao banco SQLite.

Responsabilidades:
- Criar e conectar ao banco
- Definir o schema (tabelas)
- CRUD genérico (listar, inserir, atualizar, excluir)
- Consulta com JOIN dos assistidos
"""

import sqlite3
import os

# Caminho do banco: no Android cai na pasta de dados do app
DB_PATH = os.getenv("FLET_APP_STORAGE_DATA", ".") + "/evangelizacao.db"


# ============================================================
# CONEXÃO E SCHEMA
# ============================================================
def conectar():
    """Abre conexão com SQLite e habilita foreign keys."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria todas as tabelas caso não existam."""
    with conectar() as conn:
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS igrejas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT DEFAULT '',
            endereco TEXT DEFAULT '',
            dom TEXT DEFAULT '',
            observacao TEXT DEFAULT '',
            data_cadastro TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS mensagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL UNIQUE,
            corpo TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS assistidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id INTEGER NOT NULL,
            igreja_id INTEGER,
            responsavel TEXT DEFAULT '',
            grupo TEXT DEFAULT '1',
            status TEXT DEFAULT 'Aceitou',
            data_agendada TEXT DEFAULT '',
            hora_agendada TEXT DEFAULT '',
            auxiliar TEXT DEFAULT '',
            novo_status TEXT DEFAULT '',
            observacao_cancelamento TEXT DEFAULT '',
            mensagem_id INTEGER,
            FOREIGN KEY (pessoa_id) REFERENCES pessoas(id) ON DELETE CASCADE,
            FOREIGN KEY (igreja_id) REFERENCES igrejas(id) ON DELETE SET NULL,
            FOREIGN KEY (mensagem_id) REFERENCES mensagens(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS grupos_assistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo TEXT NOT NULL UNIQUE,
            responsavel TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS grupo_auxiliares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grupo_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            FOREIGN KEY (grupo_id) REFERENCES grupos_assistencia(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS mensagem_gerada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id INTEGER NOT NULL,
            igreja_id INTEGER,
            grupo TEXT DEFAULT '',
            responsavel TEXT DEFAULT '',
            texto TEXT DEFAULT '',
            FOREIGN KEY (pessoa_id) REFERENCES pessoas(id) ON DELETE CASCADE,
            FOREIGN KEY (igreja_id) REFERENCES igrejas(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS visita_realizada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            data_realizada TEXT DEFAULT '',
            hora_realizada TEXT DEFAULT '',
            grupo TEXT DEFAULT '',
            responsavel TEXT DEFAULT '',
            registrado_em TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (pessoa_id) REFERENCES pessoas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS eventos_dom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            igreja_id INTEGER,
            dom TEXT DEFAULT '',
            visao INTEGER DEFAULT 0,
            revelacao INTEGER DEFAULT 0,
            sonho INTEGER DEFAULT 0,
            entregue_por TEXT DEFAULT '',
            grupo_servos TEXT DEFAULT '',
            visita_lar_de TEXT DEFAULT '',
            data_registro TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (igreja_id) REFERENCES igrejas(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS eventos_quantitativo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            igreja_id INTEGER,
            varoes INTEGER DEFAULT 0,
            senhoras INTEGER DEFAULT 0,
            jovens INTEGER DEFAULT 0,
            adolescentes INTEGER DEFAULT 0,
            criancas INTEGER DEFAULT 0,
            data_registro TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (igreja_id) REFERENCES igrejas(id) ON DELETE SET NULL
        );
        """)
        conn.commit()

        # Migração leve: bancos criados antes do campo dom/observacao em pessoas
        colunas = {r["name"] for r in conn.execute("PRAGMA table_info(pessoas)")}
        if "dom" not in colunas:
            conn.execute("ALTER TABLE pessoas ADD COLUMN dom TEXT DEFAULT ''")
        if "observacao" not in colunas:
            conn.execute("ALTER TABLE pessoas ADD COLUMN observacao TEXT DEFAULT ''")
        if "data_cadastro" not in colunas:
            # SQLite não aceita default não-constante em ALTER TABLE ADD COLUMN,
            # então adiciona vazio e preenche os registros existentes em seguida.
            conn.execute("ALTER TABLE pessoas ADD COLUMN data_cadastro TEXT DEFAULT ''")
            conn.execute(
                "UPDATE pessoas SET data_cadastro = datetime('now', 'localtime') "
                "WHERE data_cadastro = ''"
            )

        # Migração leve: bancos criados antes dos campos hora_agendada/auxiliar em assistidos
        colunas_assistidos = {
            r["name"] for r in conn.execute("PRAGMA table_info(assistidos)")
        }
        if "hora_agendada" not in colunas_assistidos:
            conn.execute(
                "ALTER TABLE assistidos ADD COLUMN hora_agendada TEXT DEFAULT ''"
            )
        if "auxiliar" not in colunas_assistidos:
            conn.execute("ALTER TABLE assistidos ADD COLUMN auxiliar TEXT DEFAULT ''")
        if "novo_status" not in colunas_assistidos:
            conn.execute(
                "ALTER TABLE assistidos ADD COLUMN novo_status TEXT DEFAULT ''"
            )
        if "observacao_cancelamento" not in colunas_assistidos:
            conn.execute(
                "ALTER TABLE assistidos ADD COLUMN observacao_cancelamento TEXT DEFAULT ''"
            )
        conn.commit()

        # Migração leve: bancos criados antes de grupo_auxiliares vinham com um
        # campo de texto único "auxiliares" em grupos_assistencia. Converte cada
        # linha desse texto em um registro independente de auxiliar.
        colunas_grupos = {
            r["name"] for r in conn.execute("PRAGMA table_info(grupos_assistencia)")
        }
        if "auxiliares" in colunas_grupos:
            for g in conn.execute(
                "SELECT id, auxiliares FROM grupos_assistencia"
            ).fetchall():
                ja_migrado = conn.execute(
                    "SELECT 1 FROM grupo_auxiliares WHERE grupo_id=? LIMIT 1",
                    [g["id"]],
                ).fetchone()
                if ja_migrado:
                    continue
                nomes = [
                    n.strip()
                    for n in (g["auxiliares"] or "").replace(",", "\n").splitlines()
                    if n.strip()
                ]
                for nome in nomes:
                    conn.execute(
                        "INSERT INTO grupo_auxiliares (grupo_id, nome) VALUES (?, ?)",
                        [g["id"], nome],
                    )
        conn.commit()

        # Migração leve: bancos criados antes de mensagem_gerada permitir
        # várias mensagens independentes por pessoa (pessoa_id era a chave
        # primária, uma única mensagem por pessoa). Recria a tabela com um
        # id próprio, preservando os dados existentes.
        colunas_msg_gerada = {
            r["name"] for r in conn.execute("PRAGMA table_info(mensagem_gerada)")
        }
        if colunas_msg_gerada and "id" not in colunas_msg_gerada:
            conn.execute("ALTER TABLE mensagem_gerada RENAME TO mensagem_gerada_antiga")
            conn.execute("""
                CREATE TABLE mensagem_gerada (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pessoa_id INTEGER NOT NULL,
                    igreja_id INTEGER,
                    grupo TEXT DEFAULT '',
                    responsavel TEXT DEFAULT '',
                    texto TEXT DEFAULT '',
                    FOREIGN KEY (pessoa_id) REFERENCES pessoas(id) ON DELETE CASCADE,
                    FOREIGN KEY (igreja_id) REFERENCES igrejas(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO mensagem_gerada (pessoa_id, igreja_id, grupo, responsavel, texto)
                SELECT pessoa_id, igreja_id, grupo, responsavel, texto
                FROM mensagem_gerada_antiga
            """)
            conn.execute("DROP TABLE mensagem_gerada_antiga")
        conn.commit()

        # Migração leve: bancos criados antes de eventos_dom ter igreja_id
        colunas_eventos_dom = {
            r["name"] for r in conn.execute("PRAGMA table_info(eventos_dom)")
        }
        if colunas_eventos_dom and "igreja_id" not in colunas_eventos_dom:
            conn.execute("ALTER TABLE eventos_dom ADD COLUMN igreja_id INTEGER")
        if colunas_eventos_dom and "entregue_por" not in colunas_eventos_dom:
            conn.execute(
                "ALTER TABLE eventos_dom ADD COLUMN entregue_por TEXT DEFAULT ''"
            )
        if colunas_eventos_dom and "visita_lar_de" not in colunas_eventos_dom:
            conn.execute(
                "ALTER TABLE eventos_dom ADD COLUMN visita_lar_de TEXT DEFAULT ''"
            )
        conn.commit()


# ============================================================
# CRUD GENÉRICO
# ============================================================
def listar(tabela):
    """Lista todos os registros de uma tabela, ordem decrescente por id."""
    with conectar() as conn:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {tabela} ORDER BY id DESC")]


def inserir(tabela, dados: dict):
    """Insere um registro e retorna o id gerado."""
    cols = ", ".join(dados.keys())
    ph = ", ".join(["?"] * len(dados))
    with conectar() as conn:
        cur = conn.execute(f"INSERT INTO {tabela} ({cols}) VALUES ({ph})", list(dados.values()))
        conn.commit()
        return cur.lastrowid


def atualizar(tabela, id_, dados: dict):
    """Atualiza um registro pelo id."""
    sets = ", ".join([f"{k}=?" for k in dados.keys()])
    with conectar() as conn:
        conn.execute(f"UPDATE {tabela} SET {sets} WHERE id=?", list(dados.values()) + [id_])
        conn.commit()


def excluir(tabela, id_):
    """Exclui um registro pelo id (cascata se houver FKs)."""
    with conectar() as conn:
        conn.execute(f"DELETE FROM {tabela} WHERE id=?", [id_])
        conn.commit()


def obter(tabela, id_):
    """Retorna um único registro pelo id, ou None."""
    with conectar() as conn:
        row = conn.execute(f"SELECT * FROM {tabela} WHERE id=?", [id_]).fetchone()
        return dict(row) if row else None


# ============================================================
# MENSAGEM GERADA (registros independentes, várias por pessoa)
# ============================================================
def obter_ultima_mensagem_gerada(pessoa_id):
    """Retorna a mensagem gerada mais recente para a pessoa, ou None."""
    with conectar() as conn:
        row = conn.execute(
            "SELECT * FROM mensagem_gerada WHERE pessoa_id=? ORDER BY id DESC LIMIT 1",
            [pessoa_id],
        ).fetchone()
        return dict(row) if row else None


# ============================================================
# VISITA REALIZADA (registro histórico permanente)
# ============================================================
def registrar_visita_realizada(pessoa_id, nome, data, hora, grupo, responsavel):
    """Registra permanentemente uma visita realizada (não é apagado se o
    agendamento correspondente for depois editado ou excluído)."""
    inserir(
        "visita_realizada",
        {
            "pessoa_id": pessoa_id,
            "nome": nome,
            "data_realizada": data,
            "hora_realizada": hora,
            "grupo": grupo,
            "responsavel": responsavel,
        },
    )


# ============================================================
# EVENTOS DE DOM (reunião de busca, vigília, madrugada, visita, abertura)
# ============================================================
def listar_eventos_dom(categoria: str):
    """Lista os registros de dom de uma categoria de evento (com o nome da
    igreja), mais recentes primeiro."""
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT e.*, i.nome AS igreja_nome
            FROM eventos_dom e
            LEFT JOIN igrejas i ON i.id = e.igreja_id
            WHERE e.categoria=?
            ORDER BY e.id DESC
            """,
            [categoria],
        ).fetchall()
        return [dict(r) for r in rows]


def listar_eventos_quantitativo(categoria: str):
    """Lista os registros de quantitativo de uma categoria de evento (com o
    nome da igreja), mais recentes primeiro."""
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT q.*, i.nome AS igreja_nome
            FROM eventos_quantitativo q
            LEFT JOIN igrejas i ON i.id = q.igreja_id
            WHERE q.categoria=?
            ORDER BY q.id DESC
            """,
            [categoria],
        ).fetchall()
        return [dict(r) for r in rows]


def listar_todos_eventos_dom():
    """Lista os registros de Dom de TODAS as categorias de evento (com o
    nome da igreja), mais recentes primeiro — usado no relatório consolidado
    da aba PDF."""
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT e.*, i.nome AS igreja_nome
            FROM eventos_dom e
            LEFT JOIN igrejas i ON i.id = e.igreja_id
            ORDER BY e.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def listar_todos_eventos_quantitativo():
    """Lista os registros de Quantitativo de TODAS as categorias de evento
    (com o nome da igreja), mais recentes primeiro — usado no relatório
    consolidado da aba PDF."""
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT q.*, i.nome AS igreja_nome
            FROM eventos_quantitativo q
            LEFT JOIN igrejas i ON i.id = q.igreja_id
            ORDER BY q.id DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


# ============================================================
# CONSULTAS COM JOIN
# ============================================================
def listar_assistidos_completos():
    """Retorna assistidos já com dados relacionados (pessoa, igreja, mensagem)."""
    with conectar() as conn:
        rows = conn.execute("""
            SELECT a.id, a.responsavel, a.auxiliar, a.grupo, a.status, a.data_agendada,
                   a.hora_agendada, a.novo_status, a.observacao_cancelamento,
                   p.id AS pessoa_id, p.nome, p.telefone, p.endereco,
                   p.dom, p.observacao,
                   i.id AS igreja_id, i.nome AS igreja_nome,
                   m.id AS mensagem_id, m.titulo AS mensagem_titulo
            FROM assistidos a
            JOIN pessoas p ON p.id = a.pessoa_id
            LEFT JOIN igrejas i ON i.id = a.igreja_id
            LEFT JOIN mensagens m ON m.id = a.mensagem_id
            ORDER BY a.id DESC
        """).fetchall()
        return [dict(r) for r in rows]