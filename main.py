"""
main.py — Ponto de entrada do App Evangelização.

Responsabilidades:
- Inicializar banco e estado
- Instanciar as views (uma por seção)
- Montar a navegação lateral (expansível, em overlay) e a área de conteúdo
- Rodar o app

Não contém lógica de negócio. Tudo delega para views/ e módulos.
"""

import os

import flet as ft

from backup import backup_automatico_diario
from const import APP_TITLE  # noqa: F401 (referência)
from db import init_db
from state import AppState
from views import AjudaView
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

    def _confirmar_sair(e=None) -> None:
        async def _fechar_app(e):
            page.pop_dialog()
            # `page.window.close()` só tem efeito em desktop (Windows/macOS/
            # Linux) — no Flet 0.86, é um no-op em Android/iOS porque a
            # implementação nativa é toda baseada no pacote window_manager,
            # que não existe em mobile. Em Android/iOS o jeito que realmente
            # funciona é encerrar o processo Python que roda o app.
            if page.platform in (
                ft.PagePlatform.ANDROID,
                ft.PagePlatform.ANDROID_TV,
                ft.PagePlatform.IOS,
            ):
                os._exit(0)
            else:
                await page.window.close()

        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Sair do aplicativo"),
                content=ft.Text("Deseja realmente sair?"),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                    ft.TextButton(
                        "Sair",
                        style=ft.ButtonStyle(color=ft.Colors.RED),
                        on_click=_fechar_app,
                    ),
                ],
            )
        )

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
                com_visita_lar=True,
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
        ("Ajuda", ft.Icons.HELP, AjudaView(page, state, snack)),
    ]

    # Os 3 módulos, cada um cobrindo uma faixa contígua de índices de
    # `secoes` (na ordem em que elas foram declaradas acima). Usado tanto
    # para agrupar a barra fixa de ícones quanto o menu expansível.
    MODULOS = [
        ("Pré Evento ESF", 7),
        ("Pós Evento ESF", 4),
        ("Informações", 3),
    ]
    assert sum(qtd for _, qtd in MODULOS) == len(secoes), "Módulos não cobrem todas as seções"

    indice_atual = {"valor": 0}
    conteudo = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, controls=[])
    itens_rail: list[ft.Container] = []
    itens_menu: list[ft.ListTile] = []
    modulo_aberto = [True for _ in MODULOS]

    def selecionar(indice: int) -> None:
        """Recarrega o estado e re-renderiza somente a seção escolhida,
        trocando o conteúdo exibido ao lado da navegação."""
        indice_atual["valor"] = indice
        state.recarregar()
        _, _, view = secoes[indice]
        view.render()
        conteudo.controls = [view.container]
        for i, item in enumerate(itens_rail):
            selecionado = i == indice
            item.bgcolor = (
                ft.Colors.with_opacity(0.15, ft.Colors.PRIMARY) if selecionado else None
            )
            item.content.color = ft.Colors.PRIMARY if selecionado else None
        for i, item in enumerate(itens_menu):
            item.selected = i == indice
        page.update()

    # ---------- Barra fixa de ícones (cada módulo é expansível/recolhível) ----------
    def _item_rail(indice: int, nome: str, icone: str) -> ft.Container:
        def _clicar(e):
            selecionar(indice)

        return ft.Container(
            width=RAIL_LARGURA - 16,
            height=48,
            margin=ft.Margin(8, 0, 8, 0),
            border_radius=10,
            alignment=ft.Alignment.CENTER,
            tooltip=nome,
            on_click=_clicar,
            content=ft.Icon(icone),
        )

    for i, (nome, icone, _) in enumerate(secoes):
        itens_rail.append(_item_rail(i, nome, icone))

    def _cabecalho_modulo(indice_modulo: int) -> ft.Container:
        nome_modulo, _ = MODULOS[indice_modulo]

        def _alternar(e):
            modulo_aberto[indice_modulo] = not modulo_aberto[indice_modulo]
            _montar_rail()
            page.update()

        aberto = modulo_aberto[indice_modulo]
        return ft.Container(
            width=RAIL_LARGURA - 16,
            height=28,
            margin=ft.Margin(8, 0, 8, 0),
            border_radius=8,
            alignment=ft.Alignment.CENTER,
            tooltip=f"{'Recolher' if aberto else 'Expandir'} {nome_modulo}",
            on_click=_alternar,
            content=ft.Icon(
                ft.Icons.EXPAND_LESS if aberto else ft.Icons.EXPAND_MORE,
                size=18,
                color=ft.Colors.OUTLINE,
            ),
        )

    def _montar_rail() -> None:
        controles: list[ft.Control] = []
        _cursor = 0
        for indice_modulo, (_, quantidade) in enumerate(MODULOS):
            if indice_modulo > 0:
                controles.append(
                    ft.Divider(height=10, thickness=1, leading_indent=14, trailing_indent=14)
                )
            controles.append(_cabecalho_modulo(indice_modulo))
            if modulo_aberto[indice_modulo]:
                controles.extend(itens_rail[_cursor : _cursor + quantidade])
            _cursor += quantidade
        rail_lista.controls = controles

    # `rail_topo` (botão de menu, fixo) e `rail_rodape` (botão de sair, fixo)
    # ficam fora da coluna rolável/expansível `rail_lista`, para não serem
    # perdidos quando um módulo é recolhido/expandido ou a lista rola.
    rail_topo = ft.Column(spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    rail_lista = ft.Column(
        spacing=4,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    rail_rodape = ft.Column(
        [
            ft.Divider(height=10, thickness=1, leading_indent=14, trailing_indent=14),
            ft.Container(
                width=RAIL_LARGURA - 16,
                height=48,
                margin=ft.Margin(8, 0, 8, 8),
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.12, ft.Colors.RED),
                alignment=ft.Alignment.CENTER,
                tooltip="Sair do aplicativo",
                on_click=_confirmar_sair,
                content=ft.Icon(
                    ft.Icons.POWER_SETTINGS_NEW, color=ft.Colors.RED, size=26
                ),
            ),
        ],
        spacing=0,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
    rail = ft.Container(
        width=RAIL_LARGURA,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        content=ft.Column([rail_topo, rail_lista, rail_rodape], spacing=0, expand=True),
    )
    _montar_rail()

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

    itens_menu.extend(_item_menu(i, nome, icone) for i, (nome, icone, _) in enumerate(secoes))

    grupos_menu = []
    _cursor = 0
    for titulo_modulo, quantidade in MODULOS:
        grupos_menu.append(
            ft.ExpansionTile(
                title=ft.Text(titulo_modulo, weight=ft.FontWeight.BOLD),
                expanded=True,
                controls=itens_menu[_cursor : _cursor + quantidade],
            )
        )
        _cursor += quantidade

    lista_menu = ft.Column(
        grupos_menu,
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
                ft.Divider(height=1),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.POWER_SETTINGS_NEW, color=ft.Colors.RED),
                    title=ft.Text("Sair do aplicativo", color=ft.Colors.RED),
                    on_click=lambda e: (_fechar_menu(), _confirmar_sair()),
                ),
            ],
            expand=True,
        ),
    )

    def _abrir_menu() -> None:
        for i, controle in enumerate(itens_menu):
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

    rail_topo.controls = [
        ft.IconButton(
            icon=ft.Icons.MENU,
            tooltip="Abrir menu",
            on_click=_alternar_menu,
        ),
        ft.Divider(height=10, thickness=1, leading_indent=14, trailing_indent=14),
    ]

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

    # Backup automático (no máximo 1x por dia): roda em segundo plano após a
    # tela montar, sem atrasar a abertura do app.
    page.run_task(backup_automatico_diario, page)


if __name__ == "__main__":
    ft.run(main)
