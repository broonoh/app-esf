"""
state.py — Estado em memória do app.

Mantém o cache dos dados carregados do banco e oferece
um método único para recarregar tudo.
"""

from dataclasses import dataclass, field

from db import (
    listar,
    listar_assistidos_completos,
)


@dataclass
class AppState:
    """Cache em memória dos dados do banco."""

    igrejas: list = field(default_factory=list)
    pessoas: list = field(default_factory=list)
    mensagens: list = field(default_factory=list)
    assistidos: list = field(default_factory=list)
    grupos: list = field(default_factory=list)
    grupo_auxiliares: list = field(default_factory=list)
    mensagens_geradas: list = field(default_factory=list)
    visitas_realizadas: list = field(default_factory=list)
    ultimo_pdf: str | None = None
    ultimo_pdf_realizadas: str | None = None

    def recarregar(self) -> None:
        """Recarrega todos os caches a partir do banco."""
        self.igrejas = listar("igrejas")
        self.pessoas = listar("pessoas")
        self.mensagens = listar("mensagens")
        self.assistidos = listar_assistidos_completos()
        self.grupos = sorted(listar("grupos_assistencia"), key=lambda g: g["grupo"])
        self.grupo_auxiliares = listar("grupo_auxiliares")
        self.mensagens_geradas = listar("mensagem_gerada")
        self.visitas_realizadas = listar("visita_realizada")