"""Aba de geração da mensagem final — cada mensagem é um registro independente."""

import flet as ft

from components import botao_excluir, botao_salvar, campo_grupo_remetente, titulo_secao
from db import atualizar, excluir, inserir
from mensagem import gerar_mensagem, gerar_mensagem_personalizada

MODELO_AUTOMATICO = "__automatico__"


class GerarMsgView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self.nova_pessoa = ft.Dropdown(label="Selecione o assistido", expand=True)
        self.lista = ft.Column(spacing=6)

        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Gerar Mensagem para WhatsApp"),
                    self.nova_pessoa,
                    ft.Row(
                        [
                            ft.Button(
                                "➕ Adicionar nova mensagem",
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
        if not self.nova_pessoa.value:
            self.snack("Selecione o assistido!")
            return
        inserir(
            "mensagem_gerada",
            {
                "pessoa_id": int(self.nova_pessoa.value),
                "igreja_id": None,
                "grupo": "",
                "responsavel": "",
                "texto": "",
            },
        )
        self.nova_pessoa.value = None
        self._recarregar()

    def render(self):
        self.nova_pessoa.options = [
            ft.dropdown.Option(key=str(p["id"]), text=p["nome"])
            for p in self.state.pessoas
        ]
        self.lista.controls.clear()
        for msg in self.state.mensagens_geradas:
            self.lista.controls.append(self._item_expansivel(msg))
        self.page.update()

    def _item_expansivel(self, msg: dict) -> ft.ExpansionTile:
        pessoa_atual = next(
            (p for p in self.state.pessoas if p["id"] == msg["pessoa_id"]), None
        )
        nome_atual = pessoa_atual["nome"] if pessoa_atual else "(pessoa removida)"

        campo_pessoa = ft.Dropdown(
            label="Assistido",
            expand=True,
            options=[
                ft.dropdown.Option(key=str(p["id"]), text=p["nome"])
                for p in self.state.pessoas
            ],
            value=str(msg["pessoa_id"]),
        )
        campo_igreja = ft.Dropdown(
            label="Igreja",
            expand=True,
            options=[
                ft.dropdown.Option(key=str(i["id"]), text=i["nome"])
                for i in self.state.igrejas
            ],
            value=str(msg["igreja_id"]) if msg.get("igreja_id") else None,
        )
        campo_grupo, campo_remetente = campo_grupo_remetente(
            self.page,
            self.state,
            grupo_valor=msg.get("grupo", ""),
            remetente_valor=msg.get("responsavel", ""),
        )
        campo_modelo = ft.Dropdown(
            label="Modelo de mensagem",
            expand=True,
            options=[
                ft.dropdown.Option(key=MODELO_AUTOMATICO, text="Mensagem automática"),
            ]
            + [
                ft.dropdown.Option(key=str(m["id"]), text=m["titulo"])
                for m in self.state.mensagens
            ],
            value=MODELO_AUTOMATICO,
        )
        campo_texto = ft.TextField(
            value=msg.get("texto", ""),
            multiline=True,
            min_lines=10,
            expand=True,
            read_only=True,
        )

        def _gerar(e):
            if not campo_pessoa.value:
                return
            pessoa = next(
                (
                    p
                    for p in self.state.pessoas
                    if p["id"] == int(campo_pessoa.value)
                ),
                None,
            )
            if not pessoa:
                return
            igreja_nome = ""
            if campo_igreja.value:
                ig = next(
                    (
                        x
                        for x in self.state.igrejas
                        if x["id"] == int(campo_igreja.value)
                    ),
                    None,
                )
                if ig:
                    igreja_nome = ig["nome"]

            pessoa_dados = {**pessoa, "responsavel": campo_remetente.value or ""}

            if campo_modelo.value and campo_modelo.value != MODELO_AUTOMATICO:
                m = next(
                    (
                        x
                        for x in self.state.mensagens
                        if x["id"] == int(campo_modelo.value)
                    ),
                    None,
                )
                corpo = m["corpo"] if m else ""
                campo_texto.value = gerar_mensagem_personalizada(
                    pessoa_dados, igreja_nome, corpo
                )
            else:
                campo_texto.value = gerar_mensagem(pessoa_dados, igreja_nome)
            self.page.update()

        async def _copiar(e):
            if campo_texto.value:
                await self.page.clipboard.set(campo_texto.value)
                self.snack("Mensagem copiada!")

        def _salvar(e):
            if not campo_pessoa.value:
                self.snack("Selecione o assistido!")
                return
            atualizar(
                "mensagem_gerada",
                msg["id"],
                {
                    "pessoa_id": int(campo_pessoa.value),
                    "igreja_id": int(campo_igreja.value)
                    if campo_igreja.value
                    else None,
                    "grupo": campo_grupo.value or "",
                    "responsavel": campo_remetente.value or "",
                    "texto": campo_texto.value,
                },
            )
            self._recarregar()
            self.snack("Mensagem salva! Já reflete no Agendamento.")

        def _excluir(e):
            excluir("mensagem_gerada", msg["id"])
            self._recarregar()
            self.snack("Mensagem removida!")

        resumo_linhas = (msg.get("texto") or "").strip().splitlines()
        subtitulo = resumo_linhas[0][:60] if resumo_linhas else "Nenhuma mensagem gerada ainda"

        return ft.ExpansionTile(
            title=ft.Text(nome_atual, weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(subtitulo),
            controls=[
                ft.Container(
                    padding=10,
                    content=ft.Column(
                        [
                            campo_pessoa,
                            campo_igreja,
                            campo_grupo,
                            campo_remetente,
                            campo_modelo,
                            ft.Row(
                                [
                                    ft.Button(
                                        "✍️ Gerar", on_click=_gerar, expand=True
                                    ),
                                    ft.OutlinedButton(
                                        "📋 Copiar", on_click=_copiar, expand=True
                                    ),
                                ]
                            ),
                            campo_texto,
                            ft.Row(
                                [
                                    botao_salvar(on_click=_salvar),
                                    botao_excluir(on_click=_excluir),
                                ]
                            ),
                        ],
                        spacing=8,
                    ),
                )
            ],
        )

    def _recarregar(self):
        self.state.recarregar()
        self.render()
