class MintSkinsErro(Exception):
    """Erro esperado, com mensagem pronta para mostrar ao usuario."""


class SkinSomenteLeitura(MintSkinsErro):
    pass


class SkinNaoEncontrada(MintSkinsErro):
    pass


class SkinInvalida(MintSkinsErro):
    pass


class AmbienteIncompativel(MintSkinsErro):
    pass


class NadaParaDesfazer(MintSkinsErro):
    pass


class BackupNecessario(MintSkinsErro):
    """Primeira troca: o visual atual precisa ser salvo antes de qualquer mudanca."""


class LoginNecessario(MintSkinsErro):
    pass


class CredenciaisInvalidas(MintSkinsErro):
    pass


class DadosInvalidos(MintSkinsErro):
    pass


class SemPermissao(MintSkinsErro):
    pass


class SemConexao(MintSkinsErro):
    """O site do MintSkins nao respondeu (sem internet ou fora do ar)."""


class Cancelado(MintSkinsErro):
    """A pessoa desistiu no meio (ex.: do login pelo navegador)."""
