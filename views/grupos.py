"""Aba de cadastro dos grupos de assistência (responsável e auxiliares)."""

import sqlite3

import flet as ft

from components import botao_excluir, botao_salvar, titulo_secao
from db import atualizar, excluir, inserir


class GruposView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self.grupo = ft.TextField(label="Grupo (ex: 1, 2, Jovens...)", expand=True)
        self.lista = ft.Column(spacing=6)

        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Grupo de Assistência"),
                    ft.Text(
                        "Cada grupo tem um responsável e pode ter vários auxiliares.",
                        italic=True,
                    ),
                    self.grupo,
                    ft.Row(
                        [
                            ft.Button(
                                "➕ Adicionar",
                                on_click=self._adicionar,
                                expand=True,
                            ),
                        ]
                    ),
                    ft.Divider(),
                    self.lista,
                ],
                spacing=10,
            ),
        )

    # ========================================================
    # AÇÕES — GRUPO
    # ========================================================
    def _adicionar(self, e):
        nome = self.grupo.value.strip()
        if not nome:
            self.snack("Informe o grupo!")
            return
        try:
            inserir("grupos_assistencia", {"grupo": nome})
            self.grupo.value = ""
            self._recarregar()
        except sqlite3.IntegrityError:
            self.snack("Já existe um grupo com esse nome!")

    def _salvar(self, grupo_id: int, campos: dict, e):
        nome = campos["grupo"].value.strip()
        if not nome:
            self.snack("Grupo obrigatório!")
            return
        try:
            atualizar(
                "grupos_assistencia",
                grupo_id,
                {
                    "grupo": nome,
                    "responsavel": campos["responsavel"].value.strip(),
                },
            )
            self._recarregar()
            self.snack("Grupo atualizado!")
        except sqlite3.IntegrityError:
            self.snack("Já existe um grupo com esse nome!")

    def _excluir(self, grupo_id: int, e):
        excluir("grupos_assistencia", grupo_id)
        self._recarregar()
        self.snack("Grupo removido!")

    # ========================================================
    # AÇÕES — AUXILIARES (cada um é um registro independente)
    # ========================================================
    def _adicionar_auxiliar(self, grupo_id: int, campo: ft.TextField, e):
        nome = campo.value.strip()
        if not nome:
            self.snack("Informe o nome do auxiliar!")
            return
        inserir("grupo_auxiliares", {"grupo_id": grupo_id, "nome": nome})
        self._recarregar()

    def _excluir_auxiliar(self, auxiliar_id: int, e):
        excluir("grupo_auxiliares", auxiliar_id)
        self._recarregar()
        self.snack("Auxiliar removido!")

    def _recarregar(self):
        self.state.recarregar()
        self.render()

    def render(self):
        self.lista.controls.clear()
        for g in self.state.grupos:
            self.lista.controls.append(self._item_expansivel(g))
        self.page.update()

    def _item_expansivel(self, g: dict) -> ft.ExpansionTile:
        responsavel_atual = (g.get("responsavel") or "").strip()
        auxiliares_grupo = [
            au for au in self.state.grupo_auxiliares if au["grupo_id"] == g["id"]
        ]
        resumo_auxiliares = ", ".join(au["nome"] for au in auxiliares_grupo) or "—"

        campos = {
            "grupo": ft.TextField(value=g["grupo"], label="Grupo", expand=True),
            "responsavel": ft.TextField(
                value=g.get("responsavel", ""), label="Responsável", expand=True
            ),
        }

        chips = ft.Row(
            controls=[
                ft.Chip(
                    label=ft.Text(au["nome"]),
                    delete_icon=ft.Icon(ft.Icons.CLOSE),
                    on_delete=lambda e, i=au: self._excluir_auxiliar(i["id"], e),
                )
                for au in auxiliares_grupo
            ],
            wrap=True,
            spacing=6,
        )

        novo_auxiliar = ft.TextField(label="Nome do auxiliar", expand=True)

        return ft.ExpansionTile(
            title=ft.Text(f"Grupo {g['grupo']}", weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(
                f"Responsável: {responsavel_atual or '—'} | "
                f"Auxiliares: {resumo_auxiliares}"
            ),
            controls=[
                ft.Container(
                    padding=10,
                    content=ft.Column(
                        [
                            campos["grupo"],
                            campos["responsavel"],
                            ft.Row(
                                [
                                    botao_salvar(
                                        on_click=lambda e, i=g, c=campos: self._salvar(
                                            i["id"], c, e
                                        )
                                    ),
                                    botao_excluir(
                                        on_click=lambda e, i=g: self._excluir(
                                            i["id"], e
                                        )
                                    ),
                                ]
                            ),
                            ft.Divider(height=1),
                            ft.Text("Auxiliares", weight=ft.FontWeight.BOLD),
                            chips,
                            novo_auxiliar,
                            ft.Row(
                                [
                                    ft.Button(
                                        "➕ Adicionar auxiliar",
                                        on_click=lambda e, gid=g[
                                            "id"
                                        ], c=novo_auxiliar: self._adicionar_auxiliar(
                                            gid, c, e
                                        ),
                                        expand=True,
                                    ),
                                ]
                            ),
                        ],
                        spacing=6,
                    ),
                )
            ],
        )
