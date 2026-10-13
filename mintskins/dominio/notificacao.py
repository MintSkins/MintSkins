"""Notificacoes do app (o sino da barra de titulo)."""
from dataclasses import asdict, dataclass, field
from datetime import datetime

# o que acontece ao clicar na notificacao
ACAO_ATUALIZACAO = "atualizacao"


@dataclass
class Notificacao:
    id: str
    titulo: str
    texto: str = ""
    tipo: str = "info"          # info | atualizacao | sucesso
    acao: str = ""
    criada_em: datetime = field(default_factory=lambda: datetime.now().replace(microsecond=0))
    lida: bool = False

    def para_dict(self):
        d = asdict(self)
        d["criada_em"] = self.criada_em.isoformat()
        return d

    @classmethod
    def de_dict(cls, d):
        d = dict(d)
        try:
            d["criada_em"] = datetime.fromisoformat(d.get("criada_em", ""))
        except (TypeError, ValueError):
            d.pop("criada_em", None)
        campos = cls.__dataclass_fields__
        return cls(**{k: v for k, v in d.items() if k in campos})
