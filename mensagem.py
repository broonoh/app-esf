"""
mensagem.py — Geração de texto personalizado para WhatsApp.
"""


def gerar_mensagem(pessoa: dict, igreja: str) -> str:
    """
    Gera a mensagem automática para o assistido.

    Parâmetros:
    - pessoa: dicionário com nome, responsavel e dom
    - igreja: nome da igreja a ser mencionada na mensagem

    Retorna: string pronta para copiar/enviar.
    """
    nome = pessoa.get("nome", "")
    responsavel = pessoa.get("responsavel", "")
    dom = (pessoa.get("dom") or "").strip()

    msg = f"Olá, {nome}! A Paz do Senhor Jesus!\n\n"
    msg += f"Aqui é {responsavel}, da {igreja}. Realizamos uma evangelização de rua "
    msg += "e tivemos a alegria de orar por você. Ficamos muito felizes com essa oportunidade de levarmos até você uma mensagem de Deus para sua vida!\n\n"

    if dom:
        msg += f"Durante a oração, Deus revelou um dom espiritual para sua vida: *{dom}*. "
        msg += (
            "Este dom foi uma experiência concedida por Deus para a sua vida. "
            "Não deixe para depois a oportunidade de permitir que Deus continue "
            "a se revelar para você. \n\n"
        )

    msg += ("Gostaríamos de saber se você aceita receber uma visita de alguns membros da nossa igreja em sua casa? "
            "Seria um momento simples e edificante: cantaremos alguns louvores e traremos uma breve palavra.\n\n")
    msg += ("Você não precisa se preocupar em fazer nada para receber nossos irmãos. Lembrando que será um número pequeno de irmãos, no máximo cinco pessoas. "
            "Será uma bênção para nós!\n\n")
    msg += "Podemos agendar? Qual o melhor dia e horário para você?\n\nDeus abençoe!"
    return msg


def gerar_mensagem_personalizada(pessoa: dict, igreja: str, corpo_modelo: str) -> str:
    """
    Gera a mensagem a partir de um modelo cadastrado na aba Mensagens,
    substituindo os placeholders {nome}, {responsavel} e {igreja}.

    Retorna: string pronta para copiar/enviar.
    """
    nome = pessoa.get("nome", "")
    responsavel = pessoa.get("responsavel", "")

    msg = corpo_modelo or ""
    msg = msg.replace("{nome}", nome)
    msg = msg.replace("{responsavel}", responsavel)
    msg = msg.replace("{igreja}", igreja or "")
    return msg


def gerar_mensagem_confirmacao(nome: str, data: str, hora: str = "") -> str:
    """
    Gera a mensagem de confirmação de uma visita já agendada.

    Parâmetros:
    - nome: nome do assistido
    - data: data da visita (ex: "15/03/2026")
    - hora: horário da visita (ex: "14:30"); opcional

    Retorna: string pronta para copiar/enviar.
    """
    quando = data
    if hora:
        quando += f" às {hora}"

    return (
        f"Olá, {nome}! A Paz do Senhor Jesus, tudo bem? \n\n"
        f"Passando para confirmar a nossa visita, combinada para o dia {quando}. "
        f"Será uma alegria muito grande estar com você nesse momento! \n\n"
        f"Se por algum motivo esse dia ou horário não funcionar mais para você, "
        f"é só nos avisar por aqui que a gente remarca sem problema nenhum.\n\n"
        f"Até breve! Deus abençoe! "
    )


def gerar_mensagem_programacao_cultos(nome: str) -> str:
    """
    Gera a mensagem com a programação de cultos, para convidar quem já
    recebeu a visita a conhecer a igreja.

    Retorna: string pronta para copiar/enviar.
    """
    return (
        f"Olá, {nome}! Que alegria ter estado com você! \n\n"
        f"Ficamos muito felizes com a visita e queremos te convidar para conhecer "
        f"mais de perto a nossa igreja. Segue nossa programação de cultos:\n\n"
        f"Segunda-feira: 19h30\n"
        f"Terça-feira: 19h30\n"
        f"Quarta-feira: 19h30\n"
        f"Quinta-feira: 19h30\n"
        f"Sábado: 19h\n"
        f"EBD - Domingo: 10h\n"
        f"Domingo: 19h\n\n"
        f"Será uma alegria receber você em qualquer um desses dias! Deus abençoe! "
    )
