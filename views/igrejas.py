"""Aba de cadastro de igrejas."""

import sqlite3

import flet as ft

from components import linha_edicao, titulo_secao
from db import atualizar, excluir, inserir


class IgrejasView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self.nome_field = ft.TextField(label="Nome da Igreja", expand=True)
        self.lista = ft.Column(spacing=6)

        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Cadastro de Igrejas"),
                    self.nome_field,
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

    def _adicionar(self, e):
        nome = self.nome_field.value.strip()
        if not nome:
            self.snack("Informe o nome!")
            return
        try:
            inserir("igrejas", {"nome": nome})
            self.nome_field.value = ""
            self._recarregar()
        except sqlite3.IntegrityError:
            self.snack("Igreja já cadastrada!")

    def _salvar(self, ig_id: int, campo: ft.TextField, e):
        nome = campo.value.strip()
        if not nome:
            self.snack("Nome vazio!")
            return
        atualizar("igrejas", ig_id, {"nome": nome})
        self._recarregar()
        self.snack("Igreja atualizada!")

    def _excluir(self, ig_id: int, e):
        excluir("igrejas", ig_id)
        self._recarregar()
        self.snack("Igreja removida!")

    def _recarregar(self):
        self.state.recarregar()
        self.render()

    def render(self):
        self.lista.controls.clear()
        for ig in self.state.igrejas:
            campo = ft.TextField(value=ig["nome"], expand=True)
            self.lista.controls.append(
                linha_edicao(
                    campo,
                    on_salvar=lambda e, i=ig, c=campo: self._salvar(i["id"], c, e),
                    on_excluir=lambda e, i=ig: self._excluir(i["id"], e),
                )
            )
        self.page.update()