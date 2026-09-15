"""Pacote de views — reexporta as classes para import direto."""

from views.assistidos import AssistidosView
from views.estatisticas import EstatisticasView
from views.gerar_msg import GerarMsgView
from views.grupos import GruposView
from views.igrejas import IgrejasView
from views.mensagens import MensagensView
from views.pdf import PdfView
from views.pessoas import PessoasView

__all__ = [
    "AssistidosView",
    "EstatisticasView",
    "GerarMsgView",
    "GruposView",
    "IgrejasView",
    "MensagensView",
    "PdfView",
    "PessoasView",
]
