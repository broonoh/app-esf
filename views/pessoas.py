"""Aba de cadastro do assistido (pessoa, dom e observação)."""

import asyncio
import csv
import io
import os
import subprocess
import zipfile
from datetime import datetime
from xml.etree import ElementTree as ET

import flet as ft

from components import botao_excluir, botao_salvar, titulo_secao
from db import atualizar, excluir, inserir

CAMPOS_PLANILHA = ["nome", "telefone", "endereco", "dom", "observacao"]

MODELO_XLSX_URL = "/template/cadastro_assistido.xlsx"

_NS_SS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_NS_REL = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
_ATR_RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _indice_coluna(letras: str) -> int:
    """Converte a letra da coluna do Excel (A, B, ..., Z, AA, ...) em índice 0-based."""
    indice = 0
    for ch in letras:
        indice = indice * 26 + (ord(ch.upper()) - ord("A") + 1)
    return indice - 1


def _primeira_planilha_xml(z: zipfile.ZipFile) -> str:
    """Descobre o caminho XML da primeira aba do workbook."""
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        sheet = wb.find(".//m:sheets/m:sheet", _NS_SS)
        if sheet is not None:
            rid = sheet.get(_ATR_RID)
            rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            for rel in rels.findall("r:Relationship", _NS_REL):
                if rel.get("Id") == rid:
                    alvo = rel.get("Target", "")
                    return alvo if alvo.startswith("xl/") else f"xl/{alvo}"
    except (KeyError, ET.ParseError):
        pass
    candidatos = sorted(
        n
        for n in z.namelist()
        if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
    )
    return candidatos[0] if candidatos else ""


def ler_xlsx(dados: bytes) -> list[list[str]]:
    """Lê a primeira aba de um arquivo .xlsx e retorna as linhas como listas de
    strings (sem depender de openpyxl/pandas)."""
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", _NS_SS):
                strings.append("".join(t.text or "" for t in si.findall(".//m:t", _NS_SS)))

        caminho_sheet = _primeira_planilha_xml(z)
        if not caminho_sheet or caminho_sheet not in z.namelist():
            return []

        sroot = ET.fromstring(z.read(caminho_sheet))
        linhas = []
        for row in sroot.findall(".//m:row", _NS_SS):
            valores: dict[int, str] = {}
            maior_indice = -1
            for c in row.findall("m:c", _NS_SS):
                ref = c.get("r") or ""
                letras = "".join(ch for ch in ref if ch.isalpha())
                indice = _indice_coluna(letras) if letras else maior_indice + 1
                tipo = c.get("t")
                if tipo == "inlineStr":
                    elem = c.find("m:is", _NS_SS)
                    valor = (
                        "".join(t.text or "" for t in elem.findall(".//m:t", _NS_SS))
                        if elem is not None
                        else ""
                    )
                else:
                    v = c.find("m:v", _NS_SS)
                    valor = v.text if v is not None else ""
                    if tipo == "s" and valor:
                        pos = int(valor)
                        valor = strings[pos] if pos < len(strings) else ""
                valores[indice] = valor or ""
                maior_indice = max(maior_indice, indice)
            linhas.append([valores.get(i, "") for i in range(maior_indice + 1)])
        return linhas


def ler_csv(dados: bytes) -> list[list[str]]:
    """Lê um arquivo .csv (detecta ; ou , como separador) e retorna as linhas."""
    texto = dados.decode("utf-8-sig", errors="replace")
    if not texto.strip():
        return []
    primeira_linha = texto.splitlines()[0]
    delimitador = ";" if primeira_linha.count(";") > primeira_linha.count(",") else ","
    return list(csv.reader(io.StringIO(texto), delimiter=delimitador))


def _formatar_data_cadastro(valor: str | None) -> str:
    """Formata 'YYYY-MM-DD HH:MM:SS' (formato do SQLite) como 'dd/mm/aaaa hh:mm'."""
    if not valor:
        return "—"
    try:
        data, hora = valor.split(" ")
        ano, mes, dia = data.split("-")
        return f"{dia}/{mes}/{ano} {hora[:5]}"
    except ValueError:
        return valor


def _escolher_arquivo_nativo() -> str | None:
    """Abre o seletor de arquivos nativo do sistema operacional (via zenity)
    e retorna o caminho escolhido, ou None se cancelado."""
    try:
        resultado = subprocess.run(
            [
                "zenity",
                "--file-selection",
                "--title=Selecione a planilha preenchida",
                "--file-filter=Planilhas (*.xlsx *.csv) | *.xlsx *.csv",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if resultado.returncode != 0:
        return None
    return resultado.stdout.strip() or None


class PessoasView:
    def __init__(self, page: ft.Page, state, snack):
        self.page = page
        self.state = state
        self.snack = snack

        self.nome = ft.TextField(label="Nome *", expand=True)
        self.telefone = ft.TextField(label="Telefone", expand=True)
        self.endereco = ft.TextField(label="Endereço", expand=True)
        self.dom = ft.TextField(
            label="Dons revelados",
            multiline=True,
            min_lines=3,
            max_lines=8,
            expand=True,
        )
        self.observacao = ft.TextField(
            label="Observação/Experiência",
            multiline=True,
            min_lines=3,
            max_lines=8,
            expand=True,
        )
        self.lista = ft.Column(spacing=6)

        self.container = ft.Container(
            padding=12,
            content=ft.Column(
                [
                    titulo_secao("Cadastro do Assistido"),
                    ft.ExpansionTile(
                        title=ft.Text(
                            "➕ Adicionar novo assistido", weight=ft.FontWeight.BOLD
                        ),
                        expanded=True,
                        controls=[
                            ft.Container(
                                padding=10,
                                content=ft.Column(
                                    [
                                        self.nome,
                                        self.telefone,
                                        self.endereco,
                                        self.dom,
                                        self.observacao,
                                        ft.Button(
                                            "➕ Adicionar", on_click=self._adicionar
                                        ),
                                    ],
                                    spacing=10,
                                ),
                            )
                        ],
                    ),
                    ft.ExpansionTile(
                        title=ft.Text(
                            "📋 Importar vários assistidos de uma planilha",
                            weight=ft.FontWeight.BOLD,
                        ),
                        controls=[
                            ft.Container(
                                padding=10,
                                content=ft.Column(
                                    [
                                        ft.Text(
                                            "1. Baixe o modelo de planilha (Excel). "
                                            "2. Preencha uma linha para cada assistido. "
                                            "3. Clique em 'Selecionar planilha e "
                                            "importar' e escolha o arquivo (.xlsx ou "
                                            ".csv) preenchido.",
                                            italic=True,
                                            size=11,
                                        ),
                                        ft.OutlinedButton(
                                            "⬇️ Baixar modelo de planilha (Excel)",
                                            icon=ft.Icons.DOWNLOAD,
                                            on_click=self._baixar_modelo,
                                        ),
                                        ft.Button(
                                            "📤 Selecionar planilha e importar",
                                            icon=ft.Icons.UPLOAD_FILE,
                                            on_click=self._selecionar_e_importar,
                                        ),
                                    ],
                                    spacing=8,
                                ),
                            )
                        ],
                    ),
                    ft.Divider(),
                    self.lista,
                ],
                spacing=10,
            ),
        )

    # ========================================================
    # AÇÕES
    # ========================================================
    def _adicionar(self, e):
        nome = self.nome.value.strip()
        if not nome:
            self.snack("Nome é obrigatório!")
            return
        inserir(
            "pessoas",
            {
                "nome": nome,
                "telefone": self.telefone.value.strip(),
                "endereco": self.endereco.value.strip(),
                "dom": self.dom.value.strip(),
                "observacao": self.observacao.value.strip(),
                "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        self.nome.value = ""
        self.telefone.value = ""
        self.endereco.value = ""
        self.dom.value = ""
        self.observacao.value = ""
        self._recarregar()
        self.snack("Assistido cadastrado!")

    def _salvar(self, pid: int, campos: dict, e):
        nome = campos["nome"].value.strip()
        if not nome:
            self.snack("Nome obrigatório!")
            return
        atualizar(
            "pessoas",
            pid,
            {
                "nome": nome,
                "telefone": campos["telefone"].value.strip(),
                "endereco": campos["endereco"].value.strip(),
                "dom": campos["dom"].value.strip(),
                "observacao": campos["observacao"].value.strip(),
            },
        )
        self._recarregar()
        self.snack("Assistido atualizado!")

    def _excluir(self, pid: int, e):
        excluir("pessoas", pid)
        self._recarregar()
        self.snack("Assistido removido!")

    # ========================================================
    # IMPORTAÇÃO / MODELO DE PLANILHA (baixar .xlsx, selecionar e subir)
    # ========================================================
    async def _baixar_modelo(self, e):
        if self.page.web:
            await self.page.launch_url(MODELO_XLSX_URL)
            return
        # No app nativo não há servidor web para baixar a URL — lemos o
        # modelo empacotado com o app e oferecemos a folha de "Salvar como"
        # nativa da plataforma.
        caminho_modelo = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "template",
            "cadastro_assistido.xlsx",
        )
        try:
            with open(caminho_modelo, "rb") as f:
                dados = f.read()
        except OSError:
            self.snack("Não foi possível carregar o modelo de planilha.")
            return
        await ft.FilePicker().save_file(
            file_name="cadastro_assistido.xlsx",
            src_bytes=dados,
        )

    async def _selecionar_e_importar(self, e):
        if self.page.web:
            # No navegador (teste em desktop), o FilePicker do Flet não é
            # suportado pelo cliente web — usamos o seletor nativo do SO.
            caminho = await asyncio.to_thread(_escolher_arquivo_nativo)
            if not caminho:
                return
            try:
                with open(caminho, "rb") as f:
                    dados = f.read()
            except OSError:
                self.snack("Não foi possível abrir o arquivo selecionado.")
                return
            nome_arquivo = os.path.basename(caminho).lower()
        else:
            # No app nativo (Android/iOS/desktop empacotado), o FilePicker
            # funciona normalmente através do plugin da plataforma.
            arquivos = await ft.FilePicker().pick_files(
                dialog_title="Selecione a planilha preenchida",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["xlsx", "csv"],
                allow_multiple=False,
                with_data=True,
            )
            if not arquivos:
                return
            arquivo = arquivos[0]
            dados = arquivo.bytes or b""
            nome_arquivo = (arquivo.name or "").lower()

        try:
            if nome_arquivo.endswith(".xlsx"):
                linhas = ler_xlsx(dados)
            else:
                linhas = ler_csv(dados)
        except Exception:
            self.snack(
                "Não foi possível ler o arquivo. Verifique se é um .xlsx ou .csv "
                "válido."
            )
            return

        if not linhas:
            self.snack("A planilha está vazia.")
            return

        cabecalho = [(c or "").strip().lower() for c in linhas[0]]
        if "nome" not in cabecalho:
            self.snack("A planilha precisa ter, no mínimo, a coluna 'nome'.")
            return

        indices = {
            campo: cabecalho.index(campo) if campo in cabecalho else None
            for campo in CAMPOS_PLANILHA
        }

        def _valor(linha: list, campo: str) -> str:
            indice = indices[campo]
            if indice is None or indice >= len(linha):
                return ""
            return (linha[indice] or "").strip()

        importados = 0
        ignorados = 0
        for linha in linhas[1:]:
            nome = _valor(linha, "nome")
            if not nome:
                ignorados += 1
                continue
            inserir(
                "pessoas",
                {
                    "nome": nome,
                    "telefone": _valor(linha, "telefone"),
                    "endereco": _valor(linha, "endereco"),
                    "dom": _valor(linha, "dom"),
                    "observacao": _valor(linha, "observacao"),
                    "data_cadastro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )
            importados += 1

        self._recarregar()
        if ignorados:
            self.snack(
                f"{importados} assistido(s) importado(s), {ignorados} linha(s) sem nome ignorada(s)."
            )
        else:
            self.snack(f"{importados} assistido(s) importado(s) com sucesso!")

    def _recarregar(self):
        self.state.recarregar()
        self.render()

    # ========================================================
    # RENDER
    # ========================================================
    def render(self):
        self.lista.controls.clear()
        for p in self.state.pessoas:
            self.lista.controls.append(self._item_expansivel(p))
        self.page.update()

    def _item_expansivel(self, p: dict) -> ft.ExpansionTile:
        resumo_dom = (p.get("dom") or "—").strip() or "—"
        resumo_obs = (p.get("observacao") or "—").strip() or "—"

        campos = {
            "nome": ft.TextField(value=p["nome"], label="Nome", expand=True),
            "telefone": ft.TextField(
                value=p.get("telefone", ""), label="Telefone", expand=True
            ),
            "endereco": ft.TextField(
                value=p.get("endereco", ""), label="Endereço", expand=True
            ),
            "dom": ft.TextField(
                value=p.get("dom", ""),
                label="Dons revelados",
                multiline=True,
                min_lines=3,
                max_lines=8,
                expand=True,
            ),
            "observacao": ft.TextField(
                value=p.get("observacao", ""),
                label="Observação/Experiência",
                multiline=True,
                min_lines=3,
                max_lines=8,
                expand=True,
            ),
        }

        data_cadastro = _formatar_data_cadastro(p.get("data_cadastro"))

        return ft.ExpansionTile(
            title=ft.Text(p["nome"], weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(
                f"Dons: {resumo_dom} | Obs: {resumo_obs} | Cadastrado em: {data_cadastro}"
            ),
            controls=[
                ft.Container(
                    padding=10,
                    content=ft.Column(
                        [
                            ft.Text(
                                f"Data do Cadastro: {data_cadastro}",
                                italic=True,
                                size=12,
                            ),
                            campos["nome"],
                            campos["telefone"],
                            campos["endereco"],
                            campos["dom"],
                            campos["observacao"],
                            ft.Row(
                                [
                                    botao_salvar(
                                        on_click=lambda e, i=p, c=campos: self._salvar(
                                            i["id"], c, e
                                        )
                                    ),
                                    botao_excluir(
                                        on_click=lambda e, i=p: self._excluir(i["id"], e)
                                    ),
                                ]
                            ),
                        ],
                        spacing=6,
                    ),
                )
            ],
        )
