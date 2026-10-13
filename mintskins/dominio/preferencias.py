from dataclasses import dataclass


@dataclass
class Preferencias:
    """O que acontece ao aplicar uma skin."""
    papel_de_parede: bool = True
    tela_login: bool = True
    recarregar: bool = True
    verificar_atualizacoes: bool = True
    aparencia: str = "auto"
