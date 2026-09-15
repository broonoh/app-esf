"""Aba de estatísticas: visão geral de agendamentos, visitas e cancelamentos."""

import flet as ft

from components import titulo_secao
from const import NOVO_STATUS_OPCOES, STATUS_OPCOES

_CORES_STATUS = {
    "Aceitou": "#2E7D32",
    "A realizar Contato": "#1E88E5",
    "Recusou": "#C62828",
    "Não Atendeu/Respondeu": "#EF6C00",
    "Retornar Depois": "#6D4C41",
}
_ICONES_STATUS = {
    "Aceitou": ft.Icons.CHECK_CIRCLE,
    "A realizar Contato": ft.Icons.PHONE,
    "Recusou": ft.Icons.BLOCK,
    "Não Atendeu/Respondeu": ft.Icons.PHONE_MISSED,
    "Retornar Depois": ft.Icons.SCHEDULE,
}
_CORES_NOVO_STATUS = {
    "Visita Agendada": "#8E24AA",
    "Visita Realizada": "#2E7D32",
    "Visita Cancelada": "#C62828",
}
_ICONES_NOVO_STATUS = {
    "Visita Agendada": ft.Icons.EVENT_AVAILABLE,
    "Visita Realizada": ft.Icons.CHECK_CIRCLE,
    "Visita Cancelada": ft.Icons.CANCEL,
}


def _cartao_estat(icone: str, cor: str, rotulo: str, valor: int) -> ft.Container:
    return ft.Container(
        padding=16,
        border_radius=12,
        bgcolor=cor,
        width=220,
        content=ft.Column(
            [
                ft.Icon(icone, color="white", size=26),
                ft.Text(str(valor), size=28, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text(rotulo, size=12, color="white"),
            ],
            spacing=4,
        ),
    )


class EstatisticasView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self.cartao_total = ft.Row(spacing=12, wrap=True)
        self.cartoes_status = ft.Row(spacing=12, wrap=True)
        self.cartoes_novo_status = ft.Row(spacing=12, wrap=True)
        self.lista = ft.Column(spacing=6)

        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Estatísticas"),
                    self.cartao_total,
                    ft.Divider(),
                    titulo_secao("Status do contato inicial"),
                    ft.Text(
                        "Todo agendamento entra em uma destas categorias, "
                        "assim que é cadastrado.",
                        italic=True,
                        size=11,
                    ),
                    self.cartoes_status,
                    ft.Divider(),
                    titulo_secao("Acompanhamento da visita (quando Aceitou)"),
                    ft.Text(
                        "Só existe quando o Status é 'Aceitou'. 'Visita Realizada' "
                        "aqui é histórico permanente — não some se o agendamento "
                        "mudar depois.",
                        italic=True,
                        size=11,
                    ),
                    self.cartoes_novo_status,
                    ft.Divider(),
                    titulo_secao("Assistidos — Status e Novo Status"),
                    self.lista,
                ],
                spacing=14,
            ),
        )

    def render(self):
        assistidos = self.state.assistidos
        total = len(assistidos)

        contagem_status = {s: 0 for s in STATUS_OPCOES}
        for a in assistidos:
            s = a.get("status")
            if s in contagem_status:
                contagem_status[s] += 1

        contagem_novo_status = {s: 0 for s in NOVO_STATUS_OPCOES}
        for a in assistidos:
            ns = a.get("novo_status")
            if ns in contagem_novo_status:
                contagem_novo_status[ns] += 1

        realizadas_historico = len(self.state.visitas_realizadas)

        self.cartao_total.controls = [
            _cartao_estat(
                ft.Icons.PEOPLE,
                "#0D47A1",
                "Total de agendamentos (qualquer status)",
                total,
            ),
        ]

        self.cartoes_status.controls = [
            _cartao_estat(
                _ICONES_STATUS[s],
                _CORES_STATUS[s],
                s,
                contagem_status[s],
            )
            for s in STATUS_OPCOES
        ]

        self.cartoes_novo_status.controls = [
            _cartao_estat(
                _ICONES_NOVO_STATUS["Visita Agendada"],
                _CORES_NOVO_STATUS["Visita Agendada"],
                "Visita Agendada (atual)",
                contagem_novo_status["Visita Agendada"],
            ),
            _cartao_estat(
                _ICONES_NOVO_STATUS["Visita Realizada"],
                _CORES_NOVO_STATUS["Visita Realizada"],
                "Visita Realizada (histórico)",
                realizadas_historico,
            ),
            _cartao_estat(
                _ICONES_NOVO_STATUS["Visita Cancelada"],
                _CORES_NOVO_STATUS["Visita Cancelada"],
                "Visita Cancelada (atual)",
                contagem_novo_status["Visita Cancelada"],
            ),
        ]

        self.lista.controls.clear()
        if not assistidos:
            self.lista.controls.append(
                ft.Text("Nenhum agendamento cadastrado.", italic=True)
            )
        for a in assistidos:
            self.lista.controls.append(
                ft.Container(
                    padding=10,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=8,
                    content=ft.Row(
                        [
                            ft.Text(
                                a["nome"], weight=ft.FontWeight.BOLD, expand=True
                            ),
                            ft.Text(a.get("status") or "—", size=12),
                            ft.Text(
                                a.get("novo_status") or "—", size=12, italic=True
                            ),
                        ]
                    ),
                )
            )
        self.page.update()
