"""Aba de agendamento de visitas aos assistidos — cada agendamento é um
registro independente."""

import flet as ft

from components import (
    botao_excluir,
    botao_salvar,
    campo_grupo_remetente,
    titulo_secao,
)
from const import NOVO_STATUS_OPCOES, STATUS_OPCOES
from db import (
    atualizar,
    excluir,
    inserir,
    obter,
    obter_ultima_mensagem_gerada,
    registrar_visita_realizada,
)
from mensagem import gerar_mensagem_confirmacao, gerar_mensagem_programacao_cultos


class AssistidosView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self.nova_pessoa = ft.Dropdown(label="Selecione o assistido", expand=True)

        # ---------- Filtros ----------
        self.filtro_busca = ft.TextField(
            label="🔍 Buscar por nome",
            expand=True,
            on_change=lambda e: self.render(),  # ← TextField usa on_change
        )
        self.filtro_grupo = ft.Dropdown(
            label="Grupo",
            width=120,
            value="Todos",
            on_select=lambda e: self.render(),
        )
        self.filtro_status = ft.Dropdown(
            label="Status",
            width=220,
            options=[ft.dropdown.Option("Todos")]
            + [ft.dropdown.Option(s) for s in STATUS_OPCOES]
            + [ft.dropdown.Option(s) for s in NOVO_STATUS_OPCOES],
            value="Todos",
            on_select=lambda e: self.render(),
        )

        self.lista = ft.Column(spacing=6)

        # ---------- Layout principal ----------
        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Agendamento"),
                    self.nova_pessoa,
                    ft.Row(
                        [
                            ft.Button(
                                "➕ Novo Agendamento",
                                on_click=self._adicionar,
                                expand=True,
                            ),
                        ]
                    ),
                    ft.Divider(),
                    titulo_secao("Agendamentos Cadastrados"),
                    self.filtro_busca,
                    ft.Row(
                        [
                            ft.Button(
                                "🔍 Buscar",
                                on_click=lambda e: self.render(),
                                expand=True,
                            ),
                        ]
                    ),
                    ft.Row(
                        [self.filtro_grupo, self.filtro_status], wrap=True
                    ),
                    self.lista,
                ],
                spacing=10,
            ),
        )

    # ========================================================
    # CAMPO DE DATA/HORA COM SELETOR
    # ========================================================
    def _campo_data_hora(self, valor_data: str, valor_hora: str):
        """Cria um TextField de data + hora, cada um com um botão que abre
        o respectivo seletor (calendário / relógio) do Flet."""
        campo_data = ft.TextField(
            label="Data agendada", value=valor_data, read_only=True, expand=True
        )
        campo_hora = ft.TextField(
            label="Hora agendada", value=valor_hora, read_only=True, expand=True
        )

        def _data_selecionada(e):
            if e.control.value:
                campo_data.value = e.control.value.strftime("%d/%m/%Y")
                self.page.update()

        def _hora_selecionada(e):
            if e.control.value:
                campo_hora.value = e.control.value.strftime("%H:%M")
                self.page.update()

        date_picker = ft.DatePicker(on_change=_data_selecionada)
        time_picker = ft.TimePicker(
            on_change=_hora_selecionada,
            entry_mode=ft.TimePickerEntryMode.INPUT_ONLY,
        )

        linha = ft.Column(
            [
                ft.Row(
                    [
                        campo_data,
                        ft.IconButton(
                            ft.Icons.CALENDAR_MONTH,
                            tooltip="Escolher data",
                            on_click=lambda e: self.page.show_dialog(date_picker),
                        ),
                    ]
                ),
                ft.Row(
                    [
                        campo_hora,
                        ft.IconButton(
                            ft.Icons.ACCESS_TIME,
                            tooltip="Escolher horário",
                            on_click=lambda e: self.page.show_dialog(time_picker),
                        ),
                    ]
                ),
            ],
            spacing=12,
        )
        return linha, campo_data, campo_hora

    # ========================================================
    # BLOCO CONDICIONAL: só aparece quando o Status é "Aceitou"
    # ========================================================
    def _bloco_condicional_visita(
        self,
        status_dropdown: ft.Dropdown,
        novo_status_valor: str,
        data_valor: str,
        hora_valor: str,
        obs_cancelamento_valor: str,
        nome_pessoa: str,
    ):
        data_row, campo_data, campo_hora = self._campo_data_hora(data_valor, hora_valor)

        campo_novo_status = ft.Dropdown(
            label="Novo Status",
            expand=True,
            options=[ft.dropdown.Option(s) for s in NOVO_STATUS_OPCOES],
            value=novo_status_valor or NOVO_STATUS_OPCOES[0],
        )
        campo_obs_cancelamento = ft.TextField(
            label="Observação de Cancelamento",
            value=obs_cancelamento_valor,
            multiline=True,
            min_lines=2,
            max_lines=6,
            expand=True,
            visible=campo_novo_status.value == "Visita Cancelada",
        )
        btn_confirmacao = ft.OutlinedButton(
            "✉️ Gerar mensagem de confirmação",
            on_click=lambda e: self._confirmar_visita(
                nome_pessoa, campo_data, campo_hora
            ),
            visible=campo_novo_status.value == "Visita Agendada",
        )
        btn_cultos = ft.OutlinedButton(
            "✉️ Gerar mensagem de programação de cultos",
            on_click=lambda e: self._mostrar_dialogo_mensagem(
                gerar_mensagem_programacao_cultos(nome_pessoa)
            ),
            visible=campo_novo_status.value == "Visita Realizada",
        )

        def _novo_status_mudou(e):
            campo_obs_cancelamento.visible = (
                campo_novo_status.value == "Visita Cancelada"
            )
            btn_confirmacao.visible = campo_novo_status.value == "Visita Agendada"
            btn_cultos.visible = campo_novo_status.value == "Visita Realizada"
            self.page.update()

        campo_novo_status.on_select = _novo_status_mudou

        bloco = ft.Column(
            [data_row, campo_novo_status, btn_confirmacao, btn_cultos, campo_obs_cancelamento],
            spacing=10,
            visible=status_dropdown.value == "Aceitou",
        )

        def _status_mudou(e):
            bloco.visible = status_dropdown.value == "Aceitou"
            self.page.update()

        status_dropdown.on_select = _status_mudou

        return bloco, campo_data, campo_hora, campo_novo_status, campo_obs_cancelamento

    # ========================================================
    # MENSAGENS (confirmação de visita / programação de cultos)
    # ========================================================
    def _confirmar_visita(
        self, nome: str, campo_data: ft.TextField, campo_hora: ft.TextField
    ):
        if not campo_data.value:
            self.snack("Escolha a data da visita primeiro!")
            return
        msg = gerar_mensagem_confirmacao(nome, campo_data.value, campo_hora.value)
        self._mostrar_dialogo_mensagem(msg)

    def _mostrar_dialogo_mensagem(self, msg: str):
        texto = ft.TextField(
            value=msg,
            multiline=True,
            min_lines=8,
            max_lines=14,
            read_only=True,
            expand=True,
        )

        async def _copiar(e):
            try:
                await ft.Clipboard().set(msg)
                self.snack("Mensagem copiada!")
            except Exception as ex:
                self.snack(f"Não foi possível copiar: {ex}")

        largura_dialogo = min(420, (self.page.width or 420) - 80)
        dialog = ft.AlertDialog(
            title=ft.Text("Mensagem"),
            content=ft.Container(width=largura_dialogo, content=texto),
            actions=[
                ft.TextButton("📋 Copiar", on_click=_copiar),
                ft.TextButton("Fechar", on_click=lambda e: self.page.pop_dialog()),
            ],
        )
        self.page.show_dialog(dialog)

    # ========================================================
    # AÇÕES — CADASTRO / EDIÇÃO / EXCLUSÃO
    # ========================================================
    def _adicionar(self, e):
        if not self.nova_pessoa.value:
            self.snack("Selecione o assistido!")
            return

        pessoa_id = int(self.nova_pessoa.value)
        info = obter_ultima_mensagem_gerada(pessoa_id)

        inserir(
            "assistidos",
            {
                "pessoa_id": pessoa_id,
                "igreja_id": info.get("igreja_id") if info else None,
                "responsavel": (info.get("responsavel") if info else "") or "",
                "grupo": (info.get("grupo") if info else "") or "",
                "status": "Aceitou",
                "data_agendada": "",
                "hora_agendada": "",
                "novo_status": "",
                "observacao_cancelamento": "",
            },
        )

        self.nova_pessoa.value = None
        self._recarregar()
        self.snack("Agendamento cadastrado!")

    def _salvar_item(self, assistido_id: int, campos: dict, e):
        aceitou = campos["status"].value == "Aceitou"
        novo_status_valor = campos["novo_status"].value if aceitou else ""
        cancelada = novo_status_valor == "Visita Cancelada"

        if novo_status_valor == "Visita Agendada" and (
            not campos["data"].value.strip() or not campos["hora"].value.strip()
        ):
            self.snack("Para Visita Agendada, informe a data e a hora da visita!")
            return

        anterior = obter("assistidos", assistido_id)

        atualizar(
            "assistidos",
            assistido_id,
            {
                "pessoa_id": int(campos["pessoa"].value),
                "igreja_id": int(campos["igreja"].value)
                if campos["igreja"].value
                else None,
                "responsavel": campos["remetente"].value or "",
                "grupo": campos["grupo"].value or "",
                "status": campos["status"].value,
                "data_agendada": campos["data"].value.strip() if aceitou else "",
                "hora_agendada": campos["hora"].value.strip() if aceitou else "",
                "novo_status": (campos["novo_status"].value or "")
                if aceitou
                else "",
                "observacao_cancelamento": campos["obs_cancelamento"].value.strip()
                if cancelada
                else "",
            },
        )

        # Registra permanentemente no histórico quando a visita passa a ser
        # "Visita Realizada" pela primeira vez (não duplica em salvamentos
        # seguintes, e o registro sobrevive mesmo se o agendamento mudar depois).
        if novo_status_valor == "Visita Realizada" and (
            not anterior or anterior.get("novo_status") != "Visita Realizada"
        ):
            pessoa = next(
                (
                    p
                    for p in self.state.pessoas
                    if p["id"] == int(campos["pessoa"].value)
                ),
                None,
            )
            registrar_visita_realizada(
                int(campos["pessoa"].value),
                pessoa["nome"] if pessoa else "",
                campos["data"].value.strip(),
                campos["hora"].value.strip(),
                campos["grupo"].value or "",
                campos["remetente"].value or "",
            )

        self._recarregar()
        self.snack("Agendamento atualizado!")

    def _excluir_item(self, assistido_id: int, e):
        excluir("assistidos", assistido_id)
        self._recarregar()
        self.snack("Agendamento removido!")

    def _recarregar(self):
        self.state.recarregar()
        self.render()

    # ========================================================
    # RENDER
    # ========================================================
    def _ids_pessoas_indisponiveis(self) -> set:
        """Pessoas que já recusaram, já têm visita agendada ou já tiveram
        visita realizada não ficam disponíveis para um novo agendamento."""
        return {
            a["pessoa_id"]
            for a in self.state.assistidos
            if a.get("status") == "Recusou"
            or a.get("novo_status") in ("Visita Agendada", "Visita Realizada")
        }

    def render(self):
        indisponiveis = self._ids_pessoas_indisponiveis()
        self.nova_pessoa.options = [
            ft.dropdown.Option(key=str(p["id"]), text=p["nome"])
            for p in self.state.pessoas
            if p["id"] not in indisponiveis
        ]
        self.filtro_grupo.options = [ft.dropdown.Option("Todos")] + [
            ft.dropdown.Option(g["grupo"]) for g in self.state.grupos
        ]
        self.lista.controls.clear()

        filtrados = self._filtrar()
        self.lista.controls.append(
            ft.Text(
                f"Mostrando {len(filtrados)} de {len(self.state.assistidos)} agendamentos",
                italic=True,
                size=12,
            )
        )
        if not filtrados:
            self.lista.controls.append(
                ft.Text("Nenhum agendamento encontrado.", italic=True)
            )
            self.page.update()
            return

        for a in filtrados:
            self.lista.controls.append(self._item_expansivel(a))
        self.page.update()

    def _filtrar(self):
        termo = (self.filtro_busca.value or "").strip().lower()
        f_grupo = self.filtro_grupo.value
        f_status = self.filtro_status.value
        return [
            a
            for a in self.state.assistidos
            if (not termo or termo in a["nome"].lower())
            and (f_grupo == "Todos" or a["grupo"] == f_grupo)
            and (
                f_status == "Todos"
                or a["status"] == f_status
                or a.get("novo_status") == f_status
            )
        ]

    # ========================================================
    # ITEM EXPANSÍVEL (um por agendamento)
    # ========================================================
    def _item_expansivel(self, a: dict) -> ft.ExpansionTile:
        campo_pessoa = ft.Dropdown(
            label="Pessoa",
            expand=True,
            options=[
                ft.dropdown.Option(key=str(p["id"]), text=p["nome"])
                for p in self.state.pessoas
            ],
            value=str(a["pessoa_id"]),
        )
        campo_igreja = ft.Dropdown(
            label="Igreja",
            expand=True,
            options=[
                ft.dropdown.Option(key=str(i["id"]), text=i["nome"])
                for i in self.state.igrejas
            ],
            value=str(a["igreja_id"]) if a.get("igreja_id") else None,
        )
        campo_grupo, campo_remetente = campo_grupo_remetente(
            self.page,
            self.state,
            grupo_valor=a.get("grupo", "") or "",
            remetente_valor=a.get("responsavel", "") or "",
            label_remetente="Responsável pelo Agendamento",
        )
        campo_status = ft.Dropdown(
            label="Status",
            expand=True,
            options=[ft.dropdown.Option(s) for s in STATUS_OPCOES],
            value=a.get("status") or "Aceitou",
        )
        (
            bloco_visita,
            campo_data,
            campo_hora,
            campo_novo_status,
            campo_obs_cancelamento,
        ) = self._bloco_condicional_visita(
            campo_status,
            a.get("novo_status", "") or "",
            a.get("data_agendada", "") or "",
            a.get("hora_agendada", "") or "",
            a.get("observacao_cancelamento", "") or "",
            a["nome"],
        )

        campos = {
            "pessoa": campo_pessoa,
            "igreja": campo_igreja,
            "grupo": campo_grupo,
            "remetente": campo_remetente,
            "status": campo_status,
            "data": campo_data,
            "hora": campo_hora,
            "novo_status": campo_novo_status,
            "obs_cancelamento": campo_obs_cancelamento,
        }

        subtitulo = f"{a['status']} | Grupo {a['grupo'] or '—'}"
        if a.get("novo_status"):
            subtitulo += f" | {a['novo_status']}"
        if a.get("data_agendada"):
            subtitulo += f" | Visita: {a['data_agendada']}"
            if a.get("hora_agendada"):
                subtitulo += f" às {a['hora_agendada']}"

        return ft.ExpansionTile(
            title=ft.Text(f"#{a['id']} — {a['nome']}", weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(subtitulo),
            controls=[
                ft.Container(
                    padding=10,
                    content=ft.Column(
                        [
                            campo_pessoa,
                            campo_igreja,
                            campo_grupo,
                            campo_status,
                            campo_remetente,
                            bloco_visita,
                            ft.Row(
                                [
                                    botao_salvar(
                                        on_click=lambda e, aid=a[
                                            "id"
                                        ], c=campos: self._salvar_item(aid, c, e)
                                    ),
                                    botao_excluir(
                                        on_click=lambda e, aid=a[
                                            "id"
                                        ]: self._excluir_item(aid, e)
                                    ),
                                ]
                            ),
                        ],
                        spacing=6,
                    ),
                )
            ],
        )
