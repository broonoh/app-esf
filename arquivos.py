"""
arquivos.py — Utilitários para salvar e abrir arquivos gerados (PDFs) de
forma independente de plataforma.

No navegador (web), o app tem um servidor local: salvamos em uma pasta
servida como assets e abrimos por URL relativa. No app nativo (Android/iOS/
desktop empacotado) não existe esse servidor: salvamos na pasta de dados do
app e abrimos com a folha de compartilhamento nativa (Share).
"""

import os

import flet as ft

PASTA_PUBLICA = "relatorios"


def _pasta_assets() -> str:
    base = os.getenv("FLET_ASSETS_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "assets"
    )
    pasta = os.path.join(base, PASTA_PUBLICA)
    os.makedirs(pasta, exist_ok=True)
    return pasta


def caminho_e_referencia(page: ft.Page, nome_arquivo: str) -> tuple[str, str]:
    """Retorna (caminho_em_disco, referência_para_abrir) para salvar `nome_arquivo`.

    No web, a referência é uma URL relativa servida pelo próprio app. No
    nativo, é o caminho real em disco, usado depois com o Share.
    """
    if page.web:
        caminho_disco = os.path.join(_pasta_assets(), nome_arquivo)
        referencia = f"/{PASTA_PUBLICA}/{nome_arquivo}"
    else:
        pasta = os.getenv("FLET_APP_STORAGE_DATA", ".")
        caminho_disco = os.path.join(pasta, nome_arquivo)
        referencia = caminho_disco
    return caminho_disco, referencia


async def abrir_arquivo(page: ft.Page, referencia: str) -> None:
    """Abre um arquivo gerado por `caminho_e_referencia`."""
    if page.web:
        await ft.UrlLauncher().launch_url(referencia)
    else:
        await ft.Share().share_files(
            [ft.ShareFile.from_path(referencia, name=os.path.basename(referencia))]
        )
