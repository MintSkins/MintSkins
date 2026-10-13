from dataclasses import dataclass


@dataclass
class Preferencias:
    """O que acontece ao aplicar uma skin."""
    papel_de_parede: bool = True
    tela_login: bool = True
    recarregar: bool = True
    verificar_atualizacoes: bool = True
    aparencia: str = "auto"
    iniciar_com_sistema: bool = True   # abre escondido no icone ao ligar o computador
    segundo_plano: bool = True     # fechar a janela deixa o app no icone perto do relogio
