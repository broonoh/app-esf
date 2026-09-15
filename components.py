"""
components.py — Componentes de UI reutilizáveis.

Evita repetição de blocos visuais em várias abas.
"""

import flet as ft

from const import STATUS_OPCOES


def card(titulo: str, controles: list[ft.Control]) -> ft.Container:
    """Cartão com borda e título para agrupar campos."""
    return ft.Container(
        padding=12,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        border_radius=10,
        content=ft.Column(
            [
                ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD),
                *controles,
            ],
            spacing=8,
        ),
    )


def titulo_secao(texto: str) -> ft.Text:
    """Título padrão de seção."""
    return ft.Text(texto, size=18, weight=ft.FontWeight.BOLD)


def dropdown_status(**kwargs) -> ft.Dropdown:
    """Dropdown de status já populado."""
    return ft.Dropdown(
        label="Status",
        options=[ft.dropdown.Option(s) for s in STATUS_OPCOES],
        value="Aceitou",
        **kwargs,
    )


def opcoes_remetente(state, grupo_info: dict | None) -> list[ft.dropdown.Option]:
    """Lista as opções 'Nome (Responsável)' / 'Nome (Auxiliar)' de um grupo."""
    if not grupo_info:
        return []
    opcoes = []
    responsavel = (grupo_info.get("responsavel") or "").strip()
    if responsavel:
        opcoes.append(
            ft.dropdown.Option(key=responsavel, text=f"{responsavel} (Responsável)")
        )
    auxiliares = [
        au for au in state.grupo_auxiliares if au["grupo_id"] == grupo_info["id"]
    ]
    for au in auxiliares:
        opcoes.append(
            ft.dropdown.Option(key=au["nome"], text=f"{au['nome']} (Auxiliar)")
        )
    return opcoes


def campo_grupo_remetente(
    page: ft.Page,
    state,
    grupo_valor: str = "",
    remetente_valor: str = "",
    label_remetente: str = "Quem vai enviar a mensagem",
) -> tuple[ft.Dropdown, ft.Dropdown]:
    """Cria os campos Grupo + remetente (Responsável/Auxiliar), já ligados ao
    cadastro de Grupo de Assistência: ao escolher o grupo, o segundo dropdown
    lista o responsável e os auxiliares desse grupo, para escolher UMA única
    pessoa (sem confundir responsável com auxiliar)."""
    campo_grupo = ft.Dropdown(
        label="Grupo",
        expand=True,
        options=[ft.dropdown.Option(g["grupo"]) for g in state.grupos],
        value=grupo_valor or None,
    )
    campo_remetente = ft.Dropdown(label=label_remetente, expand=True)

    grupo_info_inicial = next(
        (g for g in state.grupos if g["grupo"] == grupo_valor), None
    )
    campo_remetente.options = opcoes_remetente(state, grupo_info_inicial)
    campo_remetente.value = remetente_valor or (
        campo_remetente.options[0].key if campo_remetente.options else None
    )

    def _ao_selecionar_grupo(e):
        grupo_info = next(
            (g for g in state.grupos if g["grupo"] == campo_grupo.value), None
        )
        campo_remetente.options = opcoes_remetente(state, grupo_info)
        campo_remetente.value = (
            campo_remetente.options[0].key if campo_remetente.options else None
        )
        page.update()

    campo_grupo.on_select = _ao_selecionar_grupo
    return campo_grupo, campo_remetente


def botao_salvar(on_click, expand: bool = True) -> ft.Button:
    return ft.Button("💾 Salvar", on_click=on_click, expand=expand)


def botao_excluir(on_click, expand: bool = True) -> ft.OutlinedButton:
    return ft.OutlinedButton(
        "🗑️ Excluir",
        on_click=on_click,
        style=ft.ButtonStyle(color=ft.Colors.RED),
        expand=expand,
    )


def linha_edicao(campo: ft.TextField, on_salvar, on_excluir) -> ft.Row:
    """Linha com campo + botões de salvar/excluir (para listas simples)."""
    return ft.Row(
        [
            campo,
            ft.IconButton(ft.Icons.SAVE, on_click=on_salvar),
            ft.IconButton(
                ft.Icons.DELETE,
                icon_color=ft.Colors.RED,
                on_click=on_excluir,
            ),
        ]
    )