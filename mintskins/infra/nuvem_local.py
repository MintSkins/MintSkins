"""Nuvem local (porta Nuvem): contas, galeria e skins da conta guardadas NESTA maquina."""
import hashlib
import hmac
import json
import os
import secrets
import shutil
from datetime import datetime
from pathlib import Path

from ..dominio.conta import Conta, Perfil, validar_cadastro
from ..dominio.erros import (CredenciaisInvalidas, DadosInvalidos, LoginNecessario,
                             SemPermissao, SkinNaoEncontrada)
from ..dominio.galeria import ItemGaleria

ITERACOES = 240_000


def _hash(senha, sal):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(sal), ITERACOES).hex()


def _agora():
    return datetime.now().replace(microsecond=0)


def _data(t):
    try:
        return datetime.fromisoformat(t) if t else None
    except ValueError:
        return None


def _tamanho(pasta):
    total = 0
    for raiz, _, arqs in os.walk(pasta):
        for a in arqs:
            p = os.path.join(raiz, a)
            if not os.path.islink(p):
                total += os.path.getsize(p)
    return total


class NuvemLocal:
    def __init__(self, raiz):
        self.raiz = Path(raiz)

    def _ler(self, nome, padrao):
        try:
            return json.loads((self.raiz / nome).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return padrao

    def _gravar(self, nome, dados, privado=False):
        self.raiz.mkdir(parents=True, exist_ok=True)
        p = self.raiz / nome
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        if privado:
            tmp.chmod(0o600)
        tmp.replace(p)

    def criar_conta(self, nome, email, senha):
        nome, email = validar_cadastro(nome, email, senha)
        contas = self._ler("contas.json", {})
        if any(c["email"] == email for c in contas.values()):
            raise DadosInvalidos("Já existe uma conta com esse e-mail. Use Entrar.")
        cid = secrets.token_hex(8)
        sal = secrets.token_hex(16)
        contas[cid] = {"nome": nome, "email": email, "sal": sal, "hash": _hash(senha, sal),
                       "criada_em": _agora().isoformat()}
        self._gravar("contas.json", contas, privado=True)
        return self._abrir_sessao(cid), self._conta(cid, contas[cid])

    def entrar(self, email, senha):
        email = (email or "").strip().lower()
        for cid, c in self._ler("contas.json", {}).items():
            if c["email"] == email and hmac.compare_digest(c["hash"], _hash(senha or "", c["sal"])):
                return self._abrir_sessao(cid), self._conta(cid, c)
        raise CredenciaisInvalidas("E-mail ou senha incorretos.")

    def sair(self, token):
        sessoes = self._ler("sessoes.json", {})
        if sessoes.pop(token, None):
            self._gravar("sessoes.json", sessoes, privado=True)

    def conta(self, token):
        cid = self._ler("sessoes.json", {}).get(token or "")
        c = self._ler("contas.json", {}).get(cid) if cid else None
        return self._conta(cid, c) if c else None

    def _abrir_sessao(self, cid):
        sessoes = self._ler("sessoes.json", {})
        token = secrets.token_urlsafe(32)
        sessoes[token] = cid
        self._gravar("sessoes.json", sessoes, privado=True)
        return token

    @staticmethod
    def _conta(cid, c):
        return Conta(id=cid, nome=c["nome"], email=c["email"], criada_em=_data(c.get("criada_em")))

    def _exigir(self, token):
        conta = self.conta(token)
        if not conta:
            raise LoginNecessario("Entre na sua conta para continuar.")
        return conta

    def _pasta_item(self, item_id):
        if not item_id or Path(item_id).name != item_id or item_id.startswith("."):
            raise SkinNaoEncontrada("Skin não encontrada na galeria.")
        return self.raiz / "itens" / item_id

    def _carregar(self, item_id):
        pasta = self._pasta_item(item_id)
        try:
            d = json.loads((pasta / "item.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise SkinNaoEncontrada("Skin não encontrada na galeria.") from None
        return ItemGaleria(id=item_id, nome=d["nome"], autor_id=d["autor_id"],
                           autor_nome=d["autor_nome"], descricao=d.get("descricao", ""),
                           publica=d.get("publica", True), publicada_em=_data(d.get("publicada_em")),
                           downloads=d.get("downloads", 0), tamanho=d.get("tamanho", 0),
                           dock=d.get("dock", False), pasta=pasta / "skin",
                           favoritos=self.contagem_favoritos(item_id))

    def _salvar_item(self, item):
        pasta = self._pasta_item(item.id)
        (pasta / "item.json").write_text(json.dumps({
            "nome": item.nome, "autor_id": item.autor_id, "autor_nome": item.autor_nome,
            "descricao": item.descricao, "publica": item.publica,
            "publicada_em": item.publicada_em.isoformat() if item.publicada_em else None,
            "downloads": item.downloads, "tamanho": item.tamanho, "dock": item.dock,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

    def _todos(self):
        base = self.raiz / "itens"
        if not base.is_dir():
            return []
        itens = []
        for d in sorted(base.iterdir()):
            try:
                itens.append(self._carregar(d.name))
            except SkinNaoEncontrada:
                continue
        return itens

    def _do_dono(self, token, item_id):
        conta = self._exigir(token)
        item = self._carregar(item_id)
        if item.autor_id != conta.id:
            raise SemPermissao("Só quem enviou a skin pode alterá-la.")
        return item

    def enviar(self, token, pasta, meta, publica, item_id=None):
        conta = self._exigir(token)
        if item_id:
            item = self._do_dono(token, item_id)
        else:
            item = ItemGaleria(id=secrets.token_hex(6), nome="", autor_id=conta.id,
                               autor_nome=conta.nome, publicada_em=_agora())
        item.nome = meta.get("nome") or "Skin sem nome"
        item.descricao = meta.get("descricao", "")
        item.dock = bool(meta.get("dock"))
        item.autor_nome = conta.nome
        item.publica = publica
        destino = self._pasta_item(item.id)
        tmp = destino.with_name(destino.name + ".envio")
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        shutil.copytree(pasta, tmp / "skin", symlinks=True)
        item.tamanho = _tamanho(tmp / "skin")
        if destino.exists():
            shutil.rmtree(destino)
        tmp.rename(destino)
        self._salvar_item(item)
        return self._carregar(item.id)

    def galeria(self):
        return [i for i in self._todos() if i.publica]

    def da_conta(self, token):
        conta = self._exigir(token)
        return [i for i in self._todos() if i.autor_id == conta.id]

    def item(self, item_id, token=None):
        item = self._carregar(item_id)
        if not item.publica:
            conta = self.conta(token)
            if not conta or conta.id != item.autor_id:
                raise SkinNaoEncontrada("Skin não encontrada na galeria.")
        return item

    def baixar(self, item_id, token=None):
        item = self.item(item_id, token)
        dados = json.loads((self._pasta_item(item_id) / "item.json").read_text(encoding="utf-8"))
        dados["downloads"] = dados.get("downloads", 0) + 1
        (self._pasta_item(item_id) / "item.json").write_text(
            json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        return item.pasta

    def definir_publica(self, token, item_id, publica):
        item = self._do_dono(token, item_id)
        item.publica = publica
        self._salvar_item(item)

    def remover(self, token, item_id):
        self._do_dono(token, item_id)
        shutil.rmtree(self._pasta_item(item_id))
        favs = self._ler("favoritos.json", {})
        for lista in favs.values():
            if item_id in lista:
                lista.remove(item_id)
        self._gravar("favoritos.json", favs)

    def favoritar(self, token, item_id, favorito):
        conta = self._exigir(token)
        favs = self._ler("favoritos.json", {})
        lista = favs.setdefault(conta.id, [])
        if favorito and item_id not in lista:
            lista.append(item_id)
        elif not favorito and item_id in lista:
            lista.remove(item_id)
        self._gravar("favoritos.json", favs)

    def favoritos(self, token):
        conta = self.conta(token)
        return set(self._ler("favoritos.json", {}).get(conta.id, [])) if conta else set()

    def contagem_favoritos(self, item_id):
        return sum(item_id in lista for lista in self._ler("favoritos.json", {}).values())

    def perfil(self, autor_id):
        c = self._ler("contas.json", {}).get(autor_id)
        if not c:
            return None
        return Perfil(id=autor_id, nome=c["nome"], desde=_data(c.get("criada_em")),
                      itens=[i for i in self.galeria() if i.autor_id == autor_id])
