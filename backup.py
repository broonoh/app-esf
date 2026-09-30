"""
backup.py — Backup do banco de dados (manual, via aba PDF, e automático
uma vez por dia ao abrir o app).

O backup automático apenas copia o arquivo SQLite silenciosamente, sem
interromper a abertura do app. Para proteger os dados contra a perda do
aparelho, o usuário deve usar o botão manual na aba PDF, que abre a folha
de compartilhamento nativa para escolher um destino que não dependa do
celular (Google Drive, e-mail, etc.).
"""

import os
import shutil
from datetime import date, datetime

import flet as ft

from arquivos import caminho_e_referencia
from db import DB_PATH

_MARCADOR_ULTIMO_BACKUP = DB_PATH + ".last_backup"


def gerar_backup(page: ft.Page) -> str:
    """Copia o banco de dados para um novo arquivo de backup e retorna a
    referência (caminho/URL) pronta para abrir/compartilhar."""
    nome = f"backup_evangelizacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    caminho_disco, referencia = caminho_e_referencia(page, nome)
    shutil.copy2(DB_PATH, caminho_disco)
    return referencia


def backup_pendente_hoje() -> bool:
    """True se ainda não houve um backup automático hoje."""
    if not os.path.exists(_MARCADOR_ULTIMO_BACKUP):
        return True
    with open(_MARCADOR_ULTIMO_BACKUP) as f:
        return f.read().strip() != date.today().isoformat()


def _marcar_backup_feito() -> None:
    with open(_MARCADOR_ULTIMO_BACKUP, "w") as f:
        f.write(date.today().isoformat())


async def backup_automatico_diario(page: ft.Page) -> None:
    """Roda uma vez a cada abertura do app: se ainda não houve backup hoje,
    gera um automaticamente e silenciosamente (sem abrir a folha de
    compartilhamento). Para enviar o backup para o Google Drive, e-mail etc.,
    o usuário usa o botão manual na aba PDF."""
    if not backup_pendente_hoje():
        return
    try:
        gerar_backup(page)
        _marcar_backup_feito()
    except Exception:
        # Backup automático nunca deve travar a abertura do app.
        pass
