"""
const.py — Constantes globais do app.
Centraliza listas e valores usados em várias telas.
"""

APP_TITLE = "Cadastro ESF"
DB_FILE = "evangelizacao.db"

# Domínios controlados
STATUS_OPCOES = [
    "Aceitou",
    "A realizar Contato",
    "Recusou",
    "Não Atendeu/Respondeu",
    "Retornar Depois",
]

# Status da visita, disponível apenas quando o Status principal é "Aceitou"
NOVO_STATUS_OPCOES = [
    "Visita Agendada",
    "Visita Realizada",
    "Visita Cancelada",
]

# Placeholders aceitos nos modelos de mensagem
PLACEHOLDERS = ["{nome}", "{responsavel}", "{igreja}"]

# Categorias das abas de registro de Dom (chave salva no banco -> título da aba)
CATEGORIAS_DOM = {
    "reuniao_busca": "Reunião de Busca para ESF",
    "culto_vigilia": "Culto de Vigília para ESF",
    "madrugada_especial": "Madrugada Especial para ESF",
    "visita_lar_servos": "Visita Especial no Lar de Servos",
    "culto_abertura": "Culto de Abertura para ESF",
}