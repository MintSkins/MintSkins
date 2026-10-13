"""Estado desta maquina (porta Estado): skin ativa e preferencias."""
import json
from dataclasses import asdict, fields
from pathlib import Path

from ..dominio.preferencias import Preferencias


class EstadoArquivo:
    def __init__(self, pasta):
        self.pasta = Path(pasta)

    def _ler(self, nome):
        try:
            return json.loads((self.pasta / nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _gravar(self, nome, dados):
        self.pasta.mkdir(parents=True, exist_ok=True)
        (self.pasta / nome).write_text(json.dumps(dados, indent=2) + "\n", encoding="utf-8")

    def sessao(self):
        return self._ler("sessao.json").get("token")

    def definir_sessao(self, token):
        self._gravar("sessao.json", {"token": token} if token else {})
        (self.pasta / "sessao.json").chmod(0o600)

    def ler_valor(self, chave, padrao=None):
        return self._ler("estado.json").get(chave, padrao)

    def gravar_valor(self, chave, valor):
        dados = self._ler("estado.json")
        dados[chave] = valor
        self._gravar("estado.json", dados)

    def skin_ativa(self):
        return self._ler("estado.json").get("ativa")

    def definir_ativa(self, skin_id):
        dados = self._ler("estado.json")
        dados["ativa"] = skin_id
        self._gravar("estado.json", dados)

    def preferencias(self):
        dados = self._ler("preferencias.json")
        validos = {f.name for f in fields(Preferencias)}
        return Preferencias(**{k: v for k, v in dados.items() if k in validos})

    def gravar_preferencias(self, prefs):
        self._gravar("preferencias.json", asdict(prefs))

    def marcado(self, nome):
        return (self.pasta / nome).exists()

    def marcar(self, nome, texto=""):
        self.pasta.mkdir(parents=True, exist_ok=True)
        (self.pasta / nome).write_text(texto + "\n", encoding="utf-8")
