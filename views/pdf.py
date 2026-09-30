"""Aba de geração e compartilhamento dos relatórios PDF."""

import urllib.parse
from datetime import datetime

import flet as ft

from arquivos import abrir_arquivo, caminho_e_referencia
from backup import gerar_backup
from components import titulo_secao
from const import CATEGORIAS_DOM
from db import listar_todos_eventos_dom, listar_todos_eventos_quantitativo
from pdf_gen import (
    gerar_pdf_agendadas,
    gerar_pdf_canceladas,
    gerar_pdf_eventos_dom,
    gerar_pdf_realizadas,
)

_CAMPOS_QUANTITATIVO = ["varoes", "senhoras", "jovens", "criancas"]
_ROTULOS_QUANTITATIVO = {
    "varoes": "Varões",
    "senhoras": "Senhoras",
    "jovens": "Jovens",
    "criancas": "Cias",
}


def _resumo_classificacao(item: dict) -> str:
    marcados = [
        rotulo
        for rotulo, chave in (("Visão", "visao"), ("Revelação", "revelacao"), ("Sonho", "sonho"))
        if item.get(chave)
    ]
    return ", ".join(marcados) if marcados else "—"


def _somatorio(item: dict) -> int:
    return sum(int(item.get(campo) or 0) for campo in _CAMPOS_QUANTITATIVO)


class PdfView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self._ultimo_backup: str | None = None
        self.label_backup = ft.Text("Nenhum backup gerado ainda.", italic=True)
        self.btn_abrir_backup = ft.OutlinedButton(
            "📂 Salvar/Compartilhar Backup",
            on_click=self._abrir_backup,
            disabled=True,
            expand=True,
        )

        self.label_agendadas = ft.Text("Nenhum PDF gerado ainda.", italic=True)
        self.label_realizadas = ft.Text("Nenhum PDF gerado ainda.", italic=True)

        self.btn_abrir_agendadas = ft.OutlinedButton(
            "📂 Abrir PDF de Visitas Agendadas",
            on_click=self._abrir_agendadas,
            disabled=True,
            expand=True,
        )
        self.btn_abrir_realizadas = ft.OutlinedButton(
            "📂 Abrir PDF de Visitas Realizadas",
            on_click=self._abrir_realizadas,
            disabled=True,
            expand=True,
        )

        self._ultimo_pdf_canceladas: str | None = None
        self.label_canceladas = ft.Text("Nenhum PDF gerado ainda.", italic=True)
        self.btn_abrir_canceladas = ft.OutlinedButton(
            "📂 Abrir PDF de Visitas Canceladas",
            on_click=self._abrir_canceladas,
            disabled=True,
            expand=True,
        )

        self._ultimo_pdf_dons: str | None = None
        self.label_dons = ft.Text("Nenhum PDF gerado ainda.", italic=True)
        self.btn_abrir_dons = ft.OutlinedButton(
            "📂 Abrir PDF de Todos os Dons Cadastrados",
            on_click=self._abrir_dons,
            disabled=True,
            expand=True,
        )

        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Relatórios em PDF"),
                    ft.Text(
                        "Cada relatório é individual e sempre reflete os dados mais recentes.",
                        italic=True,
                        size=12,
                    ),
                    ft.Divider(),
                    ft.Text(
                        "💾 Backup do Banco de Dados", weight=ft.FontWeight.BOLD, size=16
                    ),
                    ft.Text(
                        "Gera uma cópia de TODOS os dados cadastrados (igrejas, "
                        "assistidos, agendamentos, doms, mensagens). Se o aparelho "
                        "for perdido ou extraviado, esse backup é o que garante que "
                        "as informações não se percam — ao salvar, escolha uma opção "
                        "que não dependa deste celular, como o Google Drive ou "
                        "enviar por e-mail. O app também gera esse backup "
                        "automaticamente uma vez por dia ao abrir, já mostrando "
                        "essa mesma tela de salvar.",
                        italic=True,
                        size=12,
                    ),
                    ft.Row(
                        [
                            ft.Button(
                                "💾 Gerar Backup do Banco de Dados",
                                on_click=self._gerar_backup,
                                expand=True,
                            )
                        ]
                    ),
                    self.label_backup,
                    ft.Row([self.btn_abrir_backup]),
                    ft.Divider(),
                    ft.Text("📅 Visitas Agendadas", weight=ft.FontWeight.BOLD, size=16),
                    ft.Row(
                        [
                            ft.Button(
                                "📄 Gerar PDF de Visitas Agendadas",
                                on_click=self._gerar_agendadas,
                                expand=True,
                            )
                        ]
                    ),
                    self.label_agendadas,
                    ft.Row([self.btn_abrir_agendadas]),
                    ft.Divider(),
                    ft.Text("✔️ Visitas Realizadas", weight=ft.FontWeight.BOLD, size=16),
                    ft.Row(
                        [
                            ft.Button(
                                "📄 Gerar PDF de Visitas Realizadas",
                                on_click=self._gerar_realizadas,
                                expand=True,
                            )
                        ]
                    ),
                    self.label_realizadas,
                    ft.Row([self.btn_abrir_realizadas]),
                    ft.Divider(),
                    ft.Text("❌ Visitas Canceladas", weight=ft.FontWeight.BOLD, size=16),
                    ft.Row(
                        [
                            ft.Button(
                                "📄 Gerar PDF de Visitas Canceladas",
                                on_click=self._gerar_canceladas,
                                expand=True,
                            )
                        ]
                    ),
                    self.label_canceladas,
                    ft.Row([self.btn_abrir_canceladas]),
                    ft.Divider(),
                    ft.Text(
                        "📖 Todos os Dons Cadastrados", weight=ft.FontWeight.BOLD, size=16
                    ),
                    ft.Text(
                        "Reúne os Doms e os Quantitativos das 5 abas de evento, "
                        "com a Igreja, o responsável pela entrega, onde foi "
                        "entregue/registrado (ex.: Reunião de Busca para ESF) e "
                        "a data do cadastro.",
                        italic=True,
                        size=12,
                    ),
                    ft.Row(
                        [
                            ft.Button(
                                "📄 Gerar PDF de Todos os Dons Cadastrados",
                                on_click=self._gerar_dons,
                                expand=True,
                            )
                        ]
                    ),
                    self.label_dons,
                    ft.Row([self.btn_abrir_dons]),
                    ft.Divider(),
                    ft.Text("Compartilhar", size=14, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "📤 Compartilhar resumo no WhatsApp",
                                on_click=self._compartilhar_whatsapp,
                                expand=True,
                            )
                        ]
                    ),
                ],
                spacing=10,
            ),
        )

    def render(self):
        """Nada a recarregar: os dados são lidos do state no momento do clique."""

    def _gerar_arquivo(self, sufixo: str) -> tuple[str, str]:
        nome = f"relatorio_{sufixo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        return caminho_e_referencia(self.page, nome)

    def _gerar_backup(self, e):
        try:
            referencia = gerar_backup(self.page)
            self._ultimo_backup = referencia
            self.label_backup.value = (
                "✅ Backup gerado! Clique abaixo e escolha o Google Drive (ou "
                "outro destino fora do aparelho) para salvar."
            )
            self.btn_abrir_backup.disabled = False
            self.snack("Backup do banco de dados gerado!")
            self.page.update()
        except Exception as ex:
            self.snack(f"Erro: {ex}")

    async def _abrir_backup(self, e):
        if not self._ultimo_backup:
            self.snack("Gere o backup primeiro!")
            return
        try:
            await abrir_arquivo(self.page, self._ultimo_backup)
        except Exception as ex:
            self.snack(f"Não foi possível abrir: {ex}")

    def _gerar_agendadas(self, e):
        try:
            self.state.recarregar()
            caminho_disco, referencia = self._gerar_arquivo("agendadas")
            gerar_pdf_agendadas(self.state.assistidos, caminho_disco)
            self.state.ultimo_pdf = referencia
            self.label_agendadas.value = "✅ PDF gerado! Clique abaixo para abrir."
            self.btn_abrir_agendadas.disabled = False
            self.snack("PDF de visitas agendadas gerado!")
            self.page.update()
        except Exception as ex:
            self.snack(f"Erro: {ex}")

    def _gerar_realizadas(self, e):
        try:
            self.state.recarregar()
            caminho_disco, referencia = self._gerar_arquivo("realizadas")
            gerar_pdf_realizadas(self.state.visitas_realizadas, caminho_disco)
            self.state.ultimo_pdf_realizadas = referencia
            self.label_realizadas.value = "✅ PDF gerado! Clique abaixo para abrir."
            self.btn_abrir_realizadas.disabled = False
            self.snack("PDF de visitas realizadas gerado!")
            self.page.update()
        except Exception as ex:
            self.snack(f"Erro: {ex}")

    def _gerar_canceladas(self, e):
        try:
            self.state.recarregar()
            caminho_disco, referencia = self._gerar_arquivo("canceladas")
            gerar_pdf_canceladas(self.state.assistidos, caminho_disco)
            self._ultimo_pdf_canceladas = referencia
            self.label_canceladas.value = "✅ PDF gerado! Clique abaixo para abrir."
            self.btn_abrir_canceladas.disabled = False
            self.snack("PDF de visitas canceladas gerado!")
            self.page.update()
        except Exception as ex:
            self.snack(f"Erro: {ex}")

    def _gerar_dons(self, e):
        try:
            self.state.recarregar()
            itens_dom = listar_todos_eventos_dom()
            for item in itens_dom:
                item["_classificacao"] = _resumo_classificacao(item)
                item["_onde_entregue"] = CATEGORIAS_DOM.get(
                    item.get("categoria"), item.get("categoria") or "—"
                )
            colunas_dom = [
                ("Igreja", "igreja_nome", 40),
                ("Dom", "dom", 50),
                ("Classificação", "_classificacao", 30),
                ("Entregue Por", "entregue_por", 30),
                ("Onde foi Entregue", "_onde_entregue", 40),
                ("Data do Cadastro", "data_registro", 30),
            ]

            itens_quant = listar_todos_eventos_quantitativo()
            for item in itens_quant:
                item["_somatorio"] = _somatorio(item)
                item["_onde_entregue"] = CATEGORIAS_DOM.get(
                    item.get("categoria"), item.get("categoria") or "—"
                )
            colunas_quant = [("Igreja", "igreja_nome", 40)]
            colunas_quant.extend(
                (_ROTULOS_QUANTITATIVO[c], c, 25) for c in _CAMPOS_QUANTITATIVO
            )
            colunas_quant.append(("Somatório", "_somatorio", 20))
            colunas_quant.append(("Onde foi Registrado", "_onde_entregue", 40))
            colunas_quant.append(("Data do Cadastro", "data_registro", 30))

            caminho_disco, referencia = self._gerar_arquivo("todos_os_dons")
            gerar_pdf_eventos_dom(
                "Todos os Dons Cadastrados",
                [
                    ("Doms cadastrados", itens_dom, colunas_dom),
                    ("Quantitativo cadastrado", itens_quant, colunas_quant),
                ],
                caminho_disco,
            )
            self._ultimo_pdf_dons = referencia
            self.label_dons.value = "✅ PDF gerado! Clique abaixo para abrir."
            self.btn_abrir_dons.disabled = False
            self.snack("PDF de todos os Dons gerado!")
            self.page.update()
        except Exception as ex:
            self.snack(f"Erro: {ex}")

    async def _abrir_dons(self, e):
        await self._abrir_pdf(self._ultimo_pdf_dons)

    async def _compartilhar_whatsapp(self, e):
        try:
            total = len(self.state.assistidos)
            agendadas = sum(
                1
                for a in self.state.assistidos
                if a.get("novo_status") == "Visita Agendada"
            )
            canceladas = sum(
                1
                for a in self.state.assistidos
                if a.get("novo_status") == "Visita Cancelada"
            )
            realizadas = len(self.state.visitas_realizadas)
            resumo = (
                f"📊 *Relatório de Evangelização*\n\n"
                f"Total de agendamentos: {total}\n"
                f"📅 Visitas agendadas: {agendadas}\n"
                f"✔️ Visitas realizadas (histórico): {realizadas}\n"
                f"❌ Visitas canceladas: {canceladas}\n\n"
                f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            )
            await ft.UrlLauncher().launch_url(
                f"https://wa.me/?text={urllib.parse.quote(resumo)}"
            )
            self.snack("Abrindo WhatsApp...")
        except Exception as ex:
            self.snack(f"Erro: {ex}")

    async def _abrir_agendadas(self, e):
        await self._abrir_pdf(self.state.ultimo_pdf)

    async def _abrir_realizadas(self, e):
        await self._abrir_pdf(self.state.ultimo_pdf_realizadas)

    async def _abrir_canceladas(self, e):
        await self._abrir_pdf(self._ultimo_pdf_canceladas)

    async def _abrir_pdf(self, referencia: str | None):
        if not referencia:
            self.snack("Gere o PDF primeiro!")
            return
        try:
            await abrir_arquivo(self.page, referencia)
        except Exception as ex:
            self.snack(f"Não foi possível abrir: {ex}")
