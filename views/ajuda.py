"""Aba de Ajuda — abre o manual do usuário (PDF) empacotado com o app."""

import os

import flet as ft

from components import titulo_secao

NOME_MANUAL = "Manual do Usuario - Cadastro ESF.pdf"


class AjudaView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Ajuda"),
                    ft.Text(
                        "Manual completo de uso do aplicativo: o que cada tela faz, "
                        "o que cada campo cadastrado significa, e para onde essa "
                        "informação vai dentro do sistema.",
                        italic=True,
                        size=12,
                    ),
                    ft.Divider(),
                    ft.Row(
                        [
                            ft.Button(
                                "📖 Abrir Manual do Usuário (PDF)",
                                on_click=self._abrir_manual,
                                expand=True,
                            )
                        ]
                    ),
                    ft.Divider(),
                    ft.Text(
                        "Desenvolvido por: Dbroonoh Software",
                        italic=True,
                        size=11,
                        color=ft.Colors.OUTLINE,
                    ),
                ],
                spacing=10,
            ),
        )

    def render(self):
        """Nada a recarregar: o manual é estático."""

    def _caminho_manual(self) -> str:
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "manual",
            "manual_usuario.pdf",
        )

    async def _abrir_manual(self, e):
        caminho = self._caminho_manual()
        if not os.path.exists(caminho):
            self.snack("Manual não encontrado.")
            return
        try:
            if self.page.web:
                await ft.UrlLauncher().launch_url("/manual/manual_usuario.pdf")
            else:
                await ft.Share().share_files(
                    [ft.ShareFile.from_path(caminho, name=NOME_MANUAL)]
                )
        except Exception as ex:
            self.snack(f"Não foi possível abrir: {ex}")
