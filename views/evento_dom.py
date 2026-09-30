"""Aba genérica de registro de Dom em eventos (Reunião de Busca, Culto de
Vigília, Madrugada Especial, Visita Especial no Lar de Servos e Culto de
Abertura). Uma mesma classe atende as 5 abas — elas só variam no título, na
categoria salva no banco e em quais seções extras aparecem. Todo registro
pertence a uma Igreja cadastrada.

O Dom (+ classificação) e o Quantitativo são cadastros independentes: cada
"Adicionar" salva só o que está na sua própria seção — adicionar um novo Dom
não mexe no Quantitativo, e vice-versa."""

from datetime import datetime

import flet as ft

from arquivos import abrir_arquivo, caminho_e_referencia
from components import botao_excluir, botao_salvar, titulo_secao
from db import (
    atualizar,
    excluir,
    inserir,
    listar_eventos_dom,
    listar_eventos_quantitativo,
)
from pdf_gen import gerar_pdf_eventos_dom

_CAMPOS_QUANTITATIVO = ["varoes", "senhoras", "jovens", "criancas"]
_ROTULOS_QUANTITATIVO = {
    "varoes": "Varões",
    "senhoras": "Senhoras",
    "jovens": "Jovens",
    "criancas": "Cias",
}


def _somatorio(item: dict) -> int:
    return sum(int(item.get(campo) or 0) for campo in _CAMPOS_QUANTITATIVO)


def _numero(valor: str) -> int:
    try:
        return int((valor or "0").strip() or 0)
    except ValueError:
        return 0


class EventoDomView:
    def __init__(
        self,
        page: ft.Page,
        state,
        snack,
        titulo: str,
        categoria: str,
        com_quantitativo: bool = False,
        com_grupo_servos: bool = False,
        com_visita_lar: bool = False,
    ):
        self.page = page
        self.state = state
        self.snack = snack
        self.titulo = titulo
        self.categoria = categoria
        self.com_quantitativo = com_quantitativo
        self.com_grupo_servos = com_grupo_servos
        self.com_visita_lar = com_visita_lar

        # ---------- Seção: novo Dom + classificação ----------
        self.igreja = ft.Dropdown(label="Igreja *", expand=True)
        self.visita_lar_de = (
            ft.TextField(label="Visita no lar de:", expand=True)
            if com_visita_lar
            else None
        )
        self.visao = ft.Checkbox(label="Visão")
        self.revelacao = ft.Checkbox(label="Revelação")
        self.sonho = ft.Checkbox(label="Sonho")

        rotulo_dom = "Dom para visita" if com_grupo_servos else "Dom para ESF"
        self.dom = ft.TextField(
            label=rotulo_dom, multiline=True, min_lines=3, max_lines=6, expand=True
        )
        self.entregue_por = ft.TextField(label="Entregue por:", expand=True)

        self.grupo_servos = (
            ft.Dropdown(label="Grupo de Servos", expand=True)
            if com_grupo_servos
            else None
        )

        controles_dom = [self.igreja]
        if self.visita_lar_de is not None:
            controles_dom.append(
                ft.Text("Visita no lar de:", weight=ft.FontWeight.BOLD)
            )
            controles_dom.append(self.visita_lar_de)
        controles_dom += [
            ft.Text("Classificar o Dom como:", weight=ft.FontWeight.BOLD),
            ft.Row([self.visao, self.revelacao, self.sonho], wrap=True),
            self.dom,
            ft.Text("Dom Entregue Por:", weight=ft.FontWeight.BOLD),
            self.entregue_por,
        ]
        if self.grupo_servos is not None:
            controles_dom.append(self.grupo_servos)
        controles_dom.append(
            ft.Row([ft.Button("➕ Adicionar", on_click=self._adicionar_dom, expand=True)])
        )

        self.lista_dom = ft.Column(spacing=6)

        secoes = [
            titulo_secao(titulo),
            ft.ExpansionTile(
                title=ft.Text("➕ Adicionar novo dom", weight=ft.FontWeight.BOLD),
                expanded=True,
                controls=[
                    ft.Container(padding=10, content=ft.Column(controles_dom, spacing=10))
                ],
            ),
        ]

        # ---------- Seção: Quantitativo (independente do Dom) ----------
        if self.com_quantitativo:
            self.igreja_quant = ft.Dropdown(label="Igreja *", expand=True)
            self.label_somatorio = ft.Text(
                "Somatório: 0", weight=ft.FontWeight.BOLD, size=15
            )

            def _atualizar_somatorio(e=None):
                total = sum(
                    _numero(self.campos_quantitativo[c].value)
                    for c in _CAMPOS_QUANTITATIVO
                )
                self.label_somatorio.value = f"Somatório: {total}"
                self.page.update()

            self.campos_quantitativo = {
                campo: ft.TextField(
                    label=_ROTULOS_QUANTITATIVO[campo],
                    expand=True,
                    keyboard_type=ft.KeyboardType.NUMBER,
                    on_change=_atualizar_somatorio,
                )
                for campo in _CAMPOS_QUANTITATIVO
            }
            self.lista_quantitativo = ft.Column(spacing=6)
            controles_quant = [
                self.igreja_quant,
                ft.Text(
                    "Quantitativo presente na igreja local",
                    weight=ft.FontWeight.BOLD,
                ),
                *[self.campos_quantitativo[c] for c in _CAMPOS_QUANTITATIVO],
                self.label_somatorio,
                ft.Row(
                    [
                        ft.Button(
                            "➕ Adicionar quantitativo",
                            on_click=self._adicionar_quantitativo,
                            expand=True,
                        )
                    ]
                ),
            ]
            secoes.append(
                ft.ExpansionTile(
                    title=ft.Text(
                        "➕ Adicionar quantitativo", weight=ft.FontWeight.BOLD
                    ),
                    expanded=True,
                    controls=[
                        ft.Container(
                            padding=10, content=ft.Column(controles_quant, spacing=10)
                        )
                    ],
                )
            )
        else:
            self.igreja_quant = None
            self.campos_quantitativo = {}
            self.lista_quantitativo = None

        # ---------- PDF ----------
        self.label_pdf = ft.Text("Nenhum PDF gerado ainda.", italic=True, size=12)
        self.btn_abrir_pdf = ft.OutlinedButton(
            "📂 Abrir PDF", on_click=self._abrir_pdf, disabled=True, expand=True
        )
        self._ultimo_pdf_ref: str | None = None

        secoes.append(
            ft.Row([ft.Button("📄 Gerar PDF", on_click=self._gerar_pdf, expand=True)])
        )
        secoes.append(self.label_pdf)
        secoes.append(ft.Row([self.btn_abrir_pdf]))
        secoes.append(ft.Divider())
        secoes.append(ft.Text("Doms cadastrados", weight=ft.FontWeight.BOLD))
        secoes.append(self.lista_dom)
        if self.lista_quantitativo is not None:
            secoes.append(ft.Divider())
            secoes.append(
                ft.Text("Quantitativo cadastrado", weight=ft.FontWeight.BOLD)
            )
            secoes.append(self.lista_quantitativo)

        self.container = ft.Container(
            padding=12, content=ft.Column(secoes, spacing=10)
        )

    # ========================================================
    # AÇÕES — DOM
    # ========================================================
    def _adicionar_dom(self, e):
        dom = self.dom.value.strip()
        if not self.igreja.value:
            self.snack("Selecione a Igreja!")
            return
        if not dom:
            self.snack("Informe o Dom!")
            return
        dados = {
            "categoria": self.categoria,
            "igreja_id": int(self.igreja.value),
            "dom": dom,
            "visao": int(bool(self.visao.value)),
            "revelacao": int(bool(self.revelacao.value)),
            "sonho": int(bool(self.sonho.value)),
            "entregue_por": self.entregue_por.value.strip(),
        }
        if self.com_grupo_servos:
            dados["grupo_servos"] = self.grupo_servos.value or ""
        if self.visita_lar_de is not None:
            dados["visita_lar_de"] = self.visita_lar_de.value.strip()
        inserir("eventos_dom", dados)
        self.dom.value = ""
        self.visao.value = False
        self.revelacao.value = False
        self.sonho.value = False
        self.entregue_por.value = ""
        if self.grupo_servos is not None:
            self.grupo_servos.value = None
        if self.visita_lar_de is not None:
            self.visita_lar_de.value = ""
        self._recarregar()
        self.snack("Dom adicionado!")

    def _salvar_dom(self, item_id: int, campos: dict, e):
        dom = campos["dom"].value.strip()
        if not campos["igreja"].value:
            self.snack("Selecione a Igreja!")
            return
        if not dom:
            self.snack("Dom obrigatório!")
            return
        dados = {
            "categoria": self.categoria,
            "igreja_id": int(campos["igreja"].value),
            "dom": dom,
            "visao": int(bool(campos["visao"].value)),
            "revelacao": int(bool(campos["revelacao"].value)),
            "sonho": int(bool(campos["sonho"].value)),
            "entregue_por": campos["entregue_por"].value.strip(),
        }
        if self.com_grupo_servos:
            dados["grupo_servos"] = (
                campos["grupo_servos"].value if campos.get("grupo_servos") else ""
            )
        if self.visita_lar_de is not None:
            dados["visita_lar_de"] = (
                campos["visita_lar_de"].value.strip()
                if campos.get("visita_lar_de")
                else ""
            )
        atualizar("eventos_dom", item_id, dados)
        self._recarregar()
        self.snack("Dom atualizado!")

    def _excluir_dom(self, item_id: int, e):
        excluir("eventos_dom", item_id)
        self._recarregar()
        self.snack("Dom removido!")

    # ========================================================
    # AÇÕES — QUANTITATIVO
    # ========================================================
    def _adicionar_quantitativo(self, e):
        if not self.igreja_quant.value:
            self.snack("Selecione a Igreja!")
            return
        valores = {
            campo: _numero(self.campos_quantitativo[campo].value)
            for campo in _CAMPOS_QUANTITATIVO
        }
        if not any(valores.values()):
            self.snack("Informe ao menos um valor no Quantitativo!")
            return
        dados = {
            "categoria": self.categoria,
            "igreja_id": int(self.igreja_quant.value),
            **valores,
        }
        inserir("eventos_quantitativo", dados)
        for campo in self.campos_quantitativo.values():
            campo.value = ""
        self.label_somatorio.value = "Somatório: 0"
        self._recarregar()
        self.snack("Quantitativo adicionado!")

    def _salvar_quantitativo(self, item_id: int, campos: dict, e):
        if not campos["igreja"].value:
            self.snack("Selecione a Igreja!")
            return
        valores = {
            campo: _numero(campos["quantitativo"][campo].value)
            for campo in _CAMPOS_QUANTITATIVO
        }
        if not any(valores.values()):
            self.snack("Informe ao menos um valor no Quantitativo!")
            return
        dados = {
            "categoria": self.categoria,
            "igreja_id": int(campos["igreja"].value),
            **valores,
        }
        atualizar("eventos_quantitativo", item_id, dados)
        self._recarregar()
        self.snack("Quantitativo atualizado!")

    def _excluir_quantitativo(self, item_id: int, e):
        excluir("eventos_quantitativo", item_id)
        self._recarregar()
        self.snack("Quantitativo removido!")

    def _recarregar(self):
        self.state.recarregar()
        self.render()

    # ========================================================
    # PDF
    # ========================================================
    def _colunas_dom(self) -> list[tuple[str, str, float]]:
        colunas = [("Igreja", "igreja_nome", 40)]
        if self.com_visita_lar:
            colunas.append(("Visita no lar de", "visita_lar_de", 35))
        colunas += [
            ("Dom", "dom", 55 if self.com_visita_lar else 65),
            ("Classificação", "_classificacao", 30 if self.com_visita_lar else 35),
            ("Entregue Por", "entregue_por", 30 if self.com_visita_lar else 35),
        ]
        if self.com_grupo_servos:
            colunas.append(("Grupo de Servos", "grupo_servos", 30))
        colunas.append(("Data do Registro", "data_registro", 30))
        return colunas

    def _colunas_quantitativo(self) -> list[tuple[str, str, float]]:
        colunas = [("Igreja", "igreja_nome", 55)]
        colunas.extend(
            (_ROTULOS_QUANTITATIVO[c], c, 30) for c in _CAMPOS_QUANTITATIVO
        )
        colunas.append(("Somatório", "_somatorio", 25))
        colunas.append(("Data do Registro", "data_registro", 40))
        return colunas

    def _gerar_pdf(self, e):
        try:
            itens_dom = listar_eventos_dom(self.categoria)
            for item in itens_dom:
                item["_classificacao"] = self._resumo_classificacao(item)
            secoes = [("Doms cadastrados", itens_dom, self._colunas_dom())]
            if self.com_quantitativo:
                itens_quant = listar_eventos_quantitativo(self.categoria)
                for item in itens_quant:
                    item["_somatorio"] = _somatorio(item)
                secoes.append(
                    ("Quantitativo cadastrado", itens_quant, self._colunas_quantitativo())
                )

            nome = (
                f"relatorio_{self.categoria}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
            caminho_disco, referencia = caminho_e_referencia(self.page, nome)
            gerar_pdf_eventos_dom(self.titulo, secoes, caminho_disco)
            self._ultimo_pdf_ref = referencia
            self.label_pdf.value = "✅ PDF gerado! Clique abaixo para abrir."
            self.btn_abrir_pdf.disabled = False
            self.snack("PDF gerado!")
            self.page.update()
        except Exception as ex:
            self.snack(f"Erro: {ex}")

    async def _abrir_pdf(self, e):
        if not self._ultimo_pdf_ref:
            self.snack("Gere o PDF primeiro!")
            return
        try:
            await abrir_arquivo(self.page, self._ultimo_pdf_ref)
        except Exception as ex:
            self.snack(f"Não foi possível abrir: {ex}")

    # ========================================================
    # RENDER
    # ========================================================
    def render(self):
        opcoes_igreja = [
            ft.dropdown.Option(key=str(i["id"]), text=i["nome"])
            for i in self.state.igrejas
        ]
        self.igreja.options = opcoes_igreja
        if self.grupo_servos is not None:
            self.grupo_servos.options = [
                ft.dropdown.Option(g["grupo"]) for g in self.state.grupos
            ]
        if self.igreja_quant is not None:
            self.igreja_quant.options = opcoes_igreja

        self.lista_dom.controls.clear()
        for item in listar_eventos_dom(self.categoria):
            self.lista_dom.controls.append(self._item_dom(item))

        if self.lista_quantitativo is not None:
            self.lista_quantitativo.controls.clear()
            for item in listar_eventos_quantitativo(self.categoria):
                self.lista_quantitativo.controls.append(self._item_quantitativo(item))

        self.page.update()

    def _resumo_classificacao(self, item: dict) -> str:
        marcados = [
            rotulo
            for rotulo, chave in (("Visão", "visao"), ("Revelação", "revelacao"), ("Sonho", "sonho"))
            if item.get(chave)
        ]
        return ", ".join(marcados) if marcados else "—"

    def _item_dom(self, item: dict) -> ft.ExpansionTile:
        campo_igreja = ft.Dropdown(
            label="Igreja",
            expand=True,
            options=[
                ft.dropdown.Option(key=str(i["id"]), text=i["nome"])
                for i in self.state.igrejas
            ],
            value=str(item["igreja_id"]) if item.get("igreja_id") else None,
        )
        campo_visita_lar_de = (
            ft.TextField(
                value=item.get("visita_lar_de", ""),
                label="Visita no lar de:",
                expand=True,
            )
            if self.com_visita_lar
            else None
        )
        campo_dom = ft.TextField(
            value=item.get("dom", ""),
            label="Dom",
            multiline=True,
            min_lines=3,
            max_lines=6,
            expand=True,
        )
        campo_visao = ft.Checkbox(label="Visão", value=bool(item.get("visao")))
        campo_revelacao = ft.Checkbox(
            label="Revelação", value=bool(item.get("revelacao"))
        )
        campo_sonho = ft.Checkbox(label="Sonho", value=bool(item.get("sonho")))
        campo_entregue_por = ft.TextField(
            value=item.get("entregue_por", ""),
            label="Entregue por: ",
            expand=True,
        )

        campos = {
            "igreja": campo_igreja,
            "dom": campo_dom,
            "visao": campo_visao,
            "revelacao": campo_revelacao,
            "sonho": campo_sonho,
            "entregue_por": campo_entregue_por,
        }
        if campo_visita_lar_de is not None:
            campos["visita_lar_de"] = campo_visita_lar_de

        controles_item = [campo_igreja]
        if campo_visita_lar_de is not None:
            controles_item.append(
                ft.Text("Visita no lar de:", weight=ft.FontWeight.BOLD)
            )
            controles_item.append(campo_visita_lar_de)
        controles_item += [
            ft.Text("Classificar o Dom como:", weight=ft.FontWeight.BOLD),
            ft.Row([campo_visao, campo_revelacao, campo_sonho], wrap=True),
            campo_dom,
            ft.Text("Dom Entregue Por:", weight=ft.FontWeight.BOLD),
            campo_entregue_por,
        ]

        if self.com_grupo_servos:
            campo_grupo_servos = ft.Dropdown(
                label="Grupo de Servos",
                expand=True,
                options=[ft.dropdown.Option(g["grupo"]) for g in self.state.grupos],
                value=item.get("grupo_servos") or None,
            )
            campos["grupo_servos"] = campo_grupo_servos
            controles_item.append(campo_grupo_servos)

        controles_item.append(
            ft.Row(
                [
                    botao_salvar(
                        on_click=lambda e, i=item["id"], c=campos: self._salvar_dom(
                            i, c, e
                        )
                    ),
                    botao_excluir(
                        on_click=lambda e, i=item["id"]: self._excluir_dom(i, e)
                    ),
                ]
            )
        )

        resumo_dom = (item.get("dom") or "").strip()
        igreja_nome = item.get("igreja_nome") or "—"
        entregue_por = (item.get("entregue_por") or "—").strip() or "—"
        subtitulo = (
            f"{igreja_nome} | {self._resumo_classificacao(item)} | "
            f"Entregue por: {entregue_por}"
        )
        if self.com_visita_lar:
            visita_lar_de = (item.get("visita_lar_de") or "—").strip() or "—"
            subtitulo = f"Visita no lar de: {visita_lar_de} | {subtitulo}"
        if resumo_dom:
            subtitulo = f"{resumo_dom[:40]} | {subtitulo}"

        return ft.ExpansionTile(
            title=ft.Text(f"Dom #{item['id']}", weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(subtitulo),
            controls=[
                ft.Container(padding=10, content=ft.Column(controles_item, spacing=6))
            ],
        )

    def _item_quantitativo(self, item: dict) -> ft.ExpansionTile:
        campo_igreja = ft.Dropdown(
            label="Igreja",
            expand=True,
            options=[
                ft.dropdown.Option(key=str(i["id"]), text=i["nome"])
                for i in self.state.igrejas
            ],
            value=str(item["igreja_id"]) if item.get("igreja_id") else None,
        )
        campos_quant = {
            campo: ft.TextField(
                value=str(item.get(campo) or 0),
                label=_ROTULOS_QUANTITATIVO[campo],
                expand=True,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            for campo in _CAMPOS_QUANTITATIVO
        }
        campos = {"igreja": campo_igreja, "quantitativo": campos_quant}

        controles_item = [
            campo_igreja,
            *[campos_quant[c] for c in _CAMPOS_QUANTITATIVO],
            ft.Row(
                [
                    botao_salvar(
                        on_click=lambda e, i=item["id"], c=campos: self._salvar_quantitativo(
                            i, c, e
                        )
                    ),
                    botao_excluir(
                        on_click=lambda e, i=item["id"]: self._excluir_quantitativo(
                            i, e
                        )
                    ),
                ]
            ),
        ]

        igreja_nome = item.get("igreja_nome") or "—"
        resumo = ", ".join(
            f"{_ROTULOS_QUANTITATIVO[c]}: {item.get(c) or 0}" for c in _CAMPOS_QUANTITATIVO
        )

        return ft.ExpansionTile(
            title=ft.Text(f"Quantitativo #{item['id']}", weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(
                f"{igreja_nome} | {resumo} | Somatório: {_somatorio(item)}"
            ),
            controls=[
                ft.Container(padding=10, content=ft.Column(controles_item, spacing=6))
            ],
        )
