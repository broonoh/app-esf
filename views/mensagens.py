"""Aba de cadastro de modelos de mensagem."""

import sqlite3

import flet as ft

from components import botao_excluir, botao_salvar, titulo_secao
from const import PLACEHOLDERS
from db import atualizar, excluir, inserir


class MensagensView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self.titulo = ft.TextField(label="Título do Modelo", expand=True)
        self.corpo = ft.TextField(
            label="Corpo da Mensagem",
            multiline=True,
            min_lines=6,
            expand=True,
        )
        self.lista = ft.Column(spacing=6)

        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Cadastro de Modelos de Mensagem"),
                    ft.Text(
                        "Placeholders aceitos: " + " ".join(PLACEHOLDERS),
                        italic=True,
                    ),
                    self.titulo,
                    self.corpo,
                    ft.Button("➕ Adicionar Modelo", on_click=self._adicionar),
                    ft.Divider(),
                    self.lista,
                ],
                spacing=10,
            ),
        )

    def _adicionar(self, e):
        titulo = self.titulo.value.strip()
        corpo = self.corpo.value.strip()
        if not titulo or not corpo:
            self.snack("Título e corpo obrigatórios!")
            return
        try:
            inserir("mensagens", {"titulo": titulo, "corpo": corpo})
            self.titulo.value = self.corpo.value = ""
            self._recarregar()
        except sqlite3.IntegrityError:
            self.snack("Já existe modelo com esse título!")

    def _salvar(self, msg_id: int, campos: dict, e):
        titulo = campos["titulo"].value.strip()
        corpo = campos["corpo"].value.strip()
        if not titulo or not corpo:
            self.snack("Título e corpo obrigatórios!")
            return
        atualizar("mensagens", msg_id, {"titulo": titulo, "corpo": corpo})
        self._recarregar()
        self.snack("Modelo atualizado!")

    def _excluir(self, msg_id: int, e):
        excluir("mensagens", msg_id)
        self._recarregar()
        self.snack("Modelo removido!")

    def _recarregar(self):
        self.state.recarregar()
        self.render()

    def render(self):
        self.lista.controls.clear()
        for m in self.state.mensagens:
            campos = {
                "titulo": ft.TextField(value=m["titulo"], label="Título", expand=True),
                "corpo": ft.TextField(
                    value=m["corpo"],
                    label="Corpo",
                    multiline=True,
                    min_lines=4,
                    expand=True,
                ),
            }
            self.lista.controls.append(
                ft.Container(
                    padding=8,
                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                    border_radius=8,
                    content=ft.Column(
                        [
                            campos["titulo"],
                            campos["corpo"],
                            ft.Row(
                                [
                                    botao_salvar(
                                        on_click=lambda e, i=m, c=campos: self._salvar(
                                            i["id"], c, e
                                        )
                                    ),
                                    botao_excluir(
                                        on_click=lambda e, i=m: self._excluir(i["id"], e)
                                    ),
                                ]
                            ),
                        ],
                        spacing=6,
                    ),
                )
            )
        self.page.update()