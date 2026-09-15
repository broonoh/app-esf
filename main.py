"""
main.py — Ponto de entrada do App Evangelização.

Responsabilidades:
- Inicializar banco e estado
- Instanciar as views (uma por seção)
- Montar a navegação lateral (expansível, em overlay) e a área de conteúdo
- Rodar o app

Não contém lógica de negócio. Tudo delega para views/ e módulos.
"""

import flet as ft

from const import APP_TITLE  # noqa: F401 (referência)
from db import init_db
from state import AppState
from views import AssistidosView
from views import EstatisticasView
from views.evento_dom import EventoDomView
from views.gerar_msg import GerarMsgView
from views import GruposView
from views import IgrejasView
from views.mensagens import MensagensView
from views import PdfView
from views import PessoasView

RAIL_LARGURA = 70
DRAWER_LARGURA = 260


def configurar_pagina(page: ft.Page) -> None:
    """Aplica configurações visuais à página."""
    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0


def construir_navegacao(page: ft.Page, state: AppState) -> ft.Stack:
    """Cria a navegação lateral: um rail estreito (sempre visível, só ícones)
    e um menu expansível que abre por cima do conteúdo (sem espremê-lo),
    ligando cada view."""

    def snack(msg: str) -> None:
        page.show_dialog(ft.SnackBar(ft.Text(msg)))

    # Instancia cada view (uma classe por seção)
    secoes = [
        ("Igrejas", ft.Icons.ACCOUNT_BALANCE, IgrejasView(page, state, snack)),
        ("Grupo de Assistência", ft.Icons.GROUPS, GruposView(page, state, snack)),
        (
            "Reunião de Busca para ESF",
            ft.Icons.TRAVEL_EXPLORE,
            EventoDomView(
                page,
                state,
                snack,
                titulo="Reunião de Busca para ESF",
                categoria="reuniao_busca",
            ),
        ),
        (
            "Culto de Vigília para ESF",
            ft.Icons.NIGHTLIGHT,
            EventoDomView(
                page,
                state,
                snack,
                titulo="Culto de Vigília para ESF",
                categoria="culto_vigilia",
                com_quantitativo=True,
            ),
        ),
        (
            "Madrugada Especial para ESF",
            ft.Icons.WB_TWILIGHT,
            EventoDomView(
                page,
                state,
                snack,
                titulo="Madrugada Especial para ESF",
                categoria="madrugada_especial",
                com_quantitativo=True,
            ),
        ),
        (
            "Visita Especial no Lar de Servos",
            ft.Icons.VOLUNTEER_ACTIVISM,
            EventoDomView(
                page,
                state,
                snack,
                titulo="Visita Especial no Lar de Servos",
                categoria="visita_lar_servos",
                com_grupo_servos=True,
            ),
        ),
        (
            "Culto de Abertura para ESF",
            ft.Icons.DOOR_FRONT_DOOR,
            EventoDomView(
                page,
                state,
                snack,
                titulo="Culto de Abertura para ESF",
                categoria="culto_abertura",
                com_quantitativo=True,
            ),
        ),
        ("Cadastro de Assistidos", ft.Icons.PEOPLE, PessoasView(page, state, snack)),
        ("Mensagens", ft.Icons.MESSAGE, MensagensView(page, state, snack)),
        ("Gerar Msg", ft.Icons.SEND, GerarMsgView(page, state, snack)),
        (
            "Agendamento de Visitas",
            ft.Icons.PERSON_ADD,
            AssistidosView(page, state, snack),
        ),
        ("Estatísticas", ft.Icons.BAR_CHART, EstatisticasView(page, state, snack)),
        ("PDF", ft.Icons.PICTURE_AS_PDF, PdfView(page, state, snack)),
    ]

    indice_atual = {"valor": 0}
    conteudo = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[])

    def selecionar(indice: int) -> None:
        """Recarrega o estado e re-renderiza somente a seção escolhida,
        trocando o conteúdo exibido ao lado da navegação."""
        indice_atual["valor"] = indice
        state.recarregar()
        _, _, view = secoes[indice]
        view.render()
        conteudo.controls = [view.container]
        rail.selected_index = indice
        page.update()

    def ao_mudar_rail(e: ft.Event) -> None:
        selecionar(e.control.selected_index)

    rail = ft.NavigationRail(
        selected_index=0,
        extended=False,
        min_width=RAIL_LARGURA,
        scrollable=True,
        label_type=ft.NavigationRailLabelType.NONE,
        destinations=[
            ft.NavigationRailDestination(icon=icone, label=nome)
            for nome, icone, _ in secoes
        ],
        on_change=ao_mudar_rail,
    )

    # ---------- Menu expansível (overlay, não empurra o conteúdo) ----------
    barreira = ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.32, ft.Colors.BLACK),
        visible=False,
        on_click=lambda e: _fechar_menu(),
    )

    def _item_menu(indice: int, nome: str, icone: str) -> ft.ListTile:
        def _ao_clicar(e):
            selecionar(indice)
            _fechar_menu()

        return ft.ListTile(
            leading=icone,
            title=ft.Text(nome),
            selected=indice == indice_atual["valor"],
            on_click=_ao_clicar,
        )

    lista_menu = ft.Column(
        [_item_menu(i, nome, icone) for i, (nome, icone, _) in enumerate(secoes)],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    drawer = ft.Container(
        width=DRAWER_LARGURA,
        left=0,
        top=0,
        bottom=0,
        visible=False,
        bgcolor=ft.Colors.SURFACE,
        shadow=ft.BoxShadow(
            blur_radius=12, color=ft.Colors.with_opacity(0.25, ft.Colors.BLACK)
        ),
        content=ft.Column(
            [
                ft.Container(
                    padding=ft.Padding(16, 16, 16, 8),
                    content=ft.Text(
                        APP_TITLE, weight=ft.FontWeight.BOLD, size=16
                    ),
                ),
                ft.Divider(height=1),
                lista_menu,
            ],
            expand=True,
        ),
    )

    def _abrir_menu() -> None:
        for i, controle in enumerate(lista_menu.controls):
            controle.selected = i == indice_atual["valor"]
        barreira.visible = True
        drawer.visible = True
        page.update()

    def _fechar_menu() -> None:
        barreira.visible = False
        drawer.visible = False
        page.update()

    def _alternar_menu(e=None) -> None:
        if drawer.visible:
            _fechar_menu()
        else:
            _abrir_menu()

    rail.leading = ft.IconButton(
        icon=ft.Icons.MENU,
        tooltip="Abrir menu",
        on_click=_alternar_menu,
    )

    # Primeira renderização
    selecionar(0)

    linha_base = ft.Row(
        expand=True,
        spacing=0,
        controls=[rail, ft.VerticalDivider(width=1), conteudo],
    )

    return ft.Stack(expand=True, controls=[linha_base, barreira, drawer])


def main(page: ft.Page) -> None:
    configurar_pagina(page)
    init_db()

    state = AppState()
    navegacao = construir_navegacao(page, state)
    # SafeArea evita que o conteúdo fique embaixo da barra de status/notch
    # ou da barra de navegação do Android (comum em celular e tablet).
    page.add(ft.SafeArea(content=navegacao, expand=True))


if __name__ == "__main__":
    ft.run(main)
