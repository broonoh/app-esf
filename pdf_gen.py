"""
pdf_gen.py — Geração dos relatórios PDF (visitas agendadas / realizadas).

Responsabilidades:
- Montar relatórios A4 paisagem com identidade visual (cabeçalho colorido,
  cartão de resumo, tabela com linhas alternadas, rodapé com paginação)
- Salvar arquivo e retornar o caminho
"""

from datetime import datetime

from fpdf import FPDF
from fpdf.enums import TableBordersLayout, TableCellFillMode
from fpdf.fonts import FontFace

# Paleta de cores do app (mesmo azul usado no splash/tema)
PRIMARY = (30, 136, 229)  # 1E88E5
PRIMARY_DARK = (13, 71, 161)  # 0D47A1
TEXT_DARK = (33, 40, 48)
TEXT_MUTED = (110, 120, 130)
ROW_ALT = (237, 243, 249)
BORDER = (214, 222, 230)

_SUBSTITUICOES = {
    "—": "-",  # travessão —
    "–": "-",  # meia-risca –
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "…": "...",
}


def _sanitize(texto) -> str:
    """Garante que o texto seja compatível com a fonte core (latin-1),
    trocando pontuação tipográfica por equivalentes simples."""
    texto = str(texto if texto is not None else "")
    for original, substituto in _SUBSTITUICOES.items():
        texto = texto.replace(original, substituto)
    return texto.encode("latin-1", "replace").decode("latin-1")


class _RelatorioPDF(FPDF):
    """FPDF com cabeçalho/rodapé de marca aplicados em toda página."""

    titulo_relatorio = ""
    subtitulo_relatorio = ""

    def header(self):
        self.set_fill_color(*PRIMARY_DARK)
        self.rect(0, 0, self.w, 24, style="F")
        self.set_fill_color(*PRIMARY)
        self.rect(0, 20, self.w, 4, style="F")

        self.set_xy(10, 6)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 8, _sanitize(self.titulo_relatorio), align="L")

        self.set_xy(10, 14)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, _sanitize(self.subtitulo_relatorio), align="L")
        self.set_y(30)
        self.set_text_color(*TEXT_DARK)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(0, 6, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="L")
        self.set_xy(-40, -12)
        self.cell(30, 6, f"Página {self.page_no()}", align="R")


def _cartao_resumo(pdf: _RelatorioPDF, itens: list[tuple[str, str]]) -> None:
    """Desenha uma fileira de cartões de resumo (rótulo + valor em destaque)."""
    largura = (pdf.w - 20) / len(itens)
    x = 10
    y = pdf.get_y()
    for rotulo, valor in itens:
        pdf.set_fill_color(245, 248, 252)
        pdf.set_draw_color(*BORDER)
        pdf.rect(x, y, largura - 4, 18, style="DF")
        pdf.set_xy(x + 3, y + 2)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(largura - 8, 5, _sanitize(rotulo.upper()))
        pdf.set_xy(x + 3, y + 7)
        pdf.set_text_color(*PRIMARY_DARK)
        pdf.set_font("Helvetica", "B", 15)
        pdf.cell(largura - 8, 8, _sanitize(valor))
        x += largura
    pdf.set_y(y + 24)
    pdf.set_text_color(*TEXT_DARK)


def _tabela(pdf: _RelatorioPDF, colunas: list[tuple[str, float]], linhas: list[list[str]]) -> None:
    """Desenha uma tabela com cabeçalho colorido e linhas em zebra.

    Usa a API de tabela nativa do fpdf2, que quebra o texto em várias linhas
    dentro da célula (em vez de cortar) e ajusta a altura da linha conforme
    o conteúdo — importante para textos longos de Dom/Observação."""
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_draw_color(*BORDER)
    with pdf.table(
        col_widths=[largura for _, largura in colunas],
        text_align="LEFT",
        borders_layout=TableBordersLayout.HORIZONTAL_LINES,
        cell_fill_mode=TableCellFillMode.EVEN_ROWS,
        cell_fill_color=ROW_ALT,
        headings_style=FontFace(
            emphasis="BOLD", color=(255, 255, 255), fill_color=PRIMARY, size_pt=9
        ),
        line_height=5,
        padding=(1.5, 2),
    ) as table:
        cabecalho = table.row()
        for titulo, _ in colunas:
            cabecalho.cell(_sanitize(titulo))
        for linha in linhas:
            fileira = table.row()
            for valor in linha:
                fileira.cell(_sanitize(valor))


def gerar_pdf_agendadas(assistidos: list, caminho_saida: str) -> str:
    """Relatório de visitas agendadas (novo_status == 'Visita Agendada')."""
    itens = [a for a in assistidos if a.get("novo_status") == "Visita Agendada"]

    pdf = _RelatorioPDF(orientation="L", unit="mm", format="A4")
    pdf.titulo_relatorio = "Visitas Agendadas"
    pdf.subtitulo_relatorio = "Relatório de evangelização — assistidos com visita marcada"
    pdf.add_page()

    _cartao_resumo(pdf, [
        ("Total agendadas", str(len(itens))),
        ("Grupos envolvidos", str(len({a.get("grupo") for a in itens if a.get("grupo")}))),
        ("Igrejas envolvidas", str(len({a.get("igreja_nome") for a in itens if a.get("igreja_nome")}))),
    ])

    colunas = [
        ("Nome", 55), ("Telefone", 32), ("Igreja", 45),
        ("Grupo", 18), ("Data", 24), ("Hora", 18), ("Responsável", 40), ("Endereço", 45),
    ]
    linhas = [
        [
            a.get("nome", "") or "",
            a.get("telefone", "") or "",
            a.get("igreja_nome", "") or "",
            a.get("grupo", "") or "—",
            a.get("data_agendada", "") or "—",
            a.get("hora_agendada", "") or "—",
            a.get("responsavel", "") or "—",
            a.get("endereco", "") or "",
        ]
        for a in itens
    ]

    if not linhas:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(0, 10, "Nenhuma visita agendada no momento.", align="C")
    else:
        _tabela(pdf, colunas, linhas)

    pdf.output(caminho_saida)
    return caminho_saida


def gerar_pdf_realizadas(visitas_realizadas: list, caminho_saida: str) -> str:
    """Relatório histórico de visitas realizadas (registro permanente)."""
    pdf = _RelatorioPDF(orientation="L", unit="mm", format="A4")
    pdf.titulo_relatorio = "Visitas Realizadas"
    pdf.subtitulo_relatorio = "Histórico permanente de visitas concluídas"
    pdf.add_page()

    grupos = {v.get("grupo") for v in visitas_realizadas if v.get("grupo")}
    _cartao_resumo(pdf, [
        ("Total realizadas", str(len(visitas_realizadas))),
        ("Grupos envolvidos", str(len(grupos))),
    ])

    colunas = [
        ("Nome", 60), ("Data da Visita", 32), ("Hora", 22),
        ("Grupo", 22), ("Responsável", 45), ("Registrado em", 45),
    ]
    linhas = [
        [
            v.get("nome", "") or "",
            v.get("data_realizada", "") or "—",
            v.get("hora_realizada", "") or "—",
            v.get("grupo", "") or "—",
            v.get("responsavel", "") or "—",
            v.get("registrado_em", "") or "",
        ]
        for v in visitas_realizadas
    ]

    if not linhas:
        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(0, 10, "Nenhuma visita realizada registrada ainda.", align="C")
    else:
        _tabela(pdf, colunas, linhas)

    pdf.output(caminho_saida)
    return caminho_saida


def gerar_pdf_eventos_dom(
    titulo: str,
    secoes: list[tuple[str, list, list[tuple[str, str, float]]]],
    caminho_saida: str,
) -> str:
    """Relatório genérico de uma das 5 abas de evento.

    `secoes` é uma lista de (subtítulo, itens, colunas), onde `colunas` é uma
    lista de (rótulo, chave_no_item, largura_mm) — por exemplo, uma seção
    para os registros de Dom e outra (opcional) para o Quantitativo.
    """
    pdf = _RelatorioPDF(orientation="L", unit="mm", format="A4")
    pdf.titulo_relatorio = titulo
    pdf.subtitulo_relatorio = "Relatório de registros do evento"
    pdf.add_page()

    total_geral = sum(len(itens) for _, itens, _ in secoes)
    igrejas = {
        item.get("igreja_nome")
        for _, itens, _ in secoes
        for item in itens
        if item.get("igreja_nome")
    }
    _cartao_resumo(pdf, [
        ("Total de registros", str(total_geral)),
        ("Igrejas envolvidas", str(len(igrejas))),
    ])

    for subtitulo, itens, colunas in secoes:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*PRIMARY_DARK)
        pdf.cell(0, 8, _sanitize(subtitulo))
        pdf.ln(10)
        pdf.set_text_color(*TEXT_DARK)

        colunas_tabela = [(rotulo, largura) for rotulo, _, largura in colunas]
        linhas = [
            [str(item.get(chave, "") or "—") for _, chave, _ in colunas]
            for item in itens
        ]

        if not linhas:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(*TEXT_MUTED)
            pdf.cell(0, 8, "Nenhum registro cadastrado ainda.")
            pdf.ln(12)
            pdf.set_text_color(*TEXT_DARK)
        else:
            _tabela(pdf, colunas_tabela, linhas)
            pdf.ln(6)

    pdf.output(caminho_saida)
    return caminho_saida
