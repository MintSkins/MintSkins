"""Nuvem pelo site (porta Nuvem): conta, galeria e skins em mintskins.com, pela API v1.

Entrar troca e-mail/@usuario + senha por um token deste computador (guardado pelo Estado).
Criar conta, trocar e-mail ou senha e confirmar a exclusao de uma skin acontecem no site,
porque pedem o codigo enviado por e-mail.
"""
import hashlib
import json
import os
import shutil
import socket
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from .. import __version__
from ..dominio.conta import Conta, Perfil
from ..dominio.erros import (CredenciaisInvalidas, DadosInvalidos, LoginNecessario, SemConexao,
                             SemPermissao, SkinNaoEncontrada)
from ..dominio.galeria import PREFIXO_OFICIAL, ItemGaleria

SITE = os.environ.get("MINTSKINS_SITE", "https://mintskins.com").rstrip("/")
TEMPO = 15
TEMPO_ENVIO = 600
PAGINAS_DA_GALERIA = 5
CACHE_DA_GALERIA = 60  # segundos


def _data(texto):
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone().replace(tzinfo=None) if texto else None
    except (ValueError, AttributeError):
        return None


class NuvemSite:
    def __init__(self, cache, computador="", site=SITE):
        self.site = site
        self.cache = Path(cache)
        self.computador = computador
        self._galeria = (0.0, [])

    # ------------------------------------------------------------------ http

    def _pedir(self, metodo, caminho, token=None, campos=None, arquivos=None, tempo=TEMPO):
        """Chama a API e devolve o JSON (ou None). Erros viram as excecoes do dominio."""
        url = caminho if caminho.startswith("http") else f"{self.site}/api/v1/{caminho}"
        cabecalhos = {"Accept": "application/json", "User-Agent": f"MintSkins/{__version__}"}
        if token:
            cabecalhos["Authorization"] = f"Bearer {token}"
        corpo = None
        if arquivos:
            corpo, tipo, tamanho = self._multipart(campos or {}, arquivos)
            cabecalhos.update({"Content-Type": tipo, "Content-Length": str(tamanho)})
        elif campos is not None:
            corpo = urllib.parse.urlencode(campos).encode()
            cabecalhos["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=corpo, headers=cabecalhos, method=metodo)
        try:
            with urllib.request.urlopen(req, timeout=tempo) as r:
                dados = r.read()
            return json.loads(dados) if dados else None
        except urllib.error.HTTPError as e:
            try:
                mensagem = json.loads(e.read() or b"{}").get("erro")
            except ValueError:
                mensagem = None
            raise self._erro(e.code, mensagem) from None
        except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
            raise SemConexao("Não deu para falar com o mintskins.com. Confira a internet e tente de novo.") from e
        finally:
            if corpo is not None and hasattr(corpo, "close"):
                corpo.close()

    @staticmethod
    def _erro(codigo, mensagem):
        if codigo == 401:
            return LoginNecessario(mensagem or "Entre na sua conta para continuar.")
        if codigo == 403:
            return SemPermissao(mensagem or "Você não pode fazer isso.")
        if codigo == 404:
            return SkinNaoEncontrada(mensagem or "Skin não encontrada na galeria.")
        if codigo == 413:
            return DadosInvalidos("A skin passa do tamanho máximo aceito pelo site.")
        if codigo in (422, 429):
            return DadosInvalidos(mensagem or "O site recusou o pedido.")
        return SemConexao(mensagem or f"O mintskins.com respondeu com erro ({codigo}). Tente de novo mais tarde.")

    def _multipart(self, campos, arquivos):
        """Monta o corpo multipart num arquivo temporario (a skin pode ter dezenas de MB)."""
        limite = uuid.uuid4().hex
        corpo = tempfile.TemporaryFile()
        for nome, valor in campos.items():
            corpo.write(f'--{limite}\r\nContent-Disposition: form-data; name="{nome}"\r\n\r\n{valor}\r\n'.encode())
        for nome, (arquivo, nome_do_arquivo, tipo) in arquivos.items():
            corpo.write(f'--{limite}\r\nContent-Disposition: form-data; name="{nome}"; '
                        f'filename="{nome_do_arquivo}"\r\nContent-Type: {tipo}\r\n\r\n'.encode())
            with open(arquivo, "rb") as f:
                shutil.copyfileobj(f, corpo)
            corpo.write(b"\r\n")
        corpo.write(f"--{limite}--\r\n".encode())
        tamanho = corpo.tell()
        corpo.seek(0)
        return corpo, f"multipart/form-data; boundary={limite}", tamanho

    def _baixar_arquivo(self, url, destino, token=None):
        cabecalhos = {"User-Agent": f"MintSkins/{__version__}"}
        if token and url.startswith(self.site):
            cabecalhos["Authorization"] = f"Bearer {token}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=cabecalhos), timeout=TEMPO_ENVIO) as r, \
                    open(destino, "wb") as f:
                shutil.copyfileobj(r, f)
        except urllib.error.HTTPError as e:
            raise self._erro(e.code, None) from None
        except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
            raise SemConexao("Não deu para baixar do mintskins.com. Confira a internet e tente de novo.") from e
        return Path(destino)

    def _imagem(self, url, pasta, nome):
        """Baixa a imagem uma vez (o nome do arquivo segue a URL) e devolve o caminho, ou None."""
        if not url:
            return None
        pasta = self.cache / pasta
        destino = pasta / f"{nome}-{hashlib.sha1(url.split('?')[0].encode()).hexdigest()[:12]}.img"
        if not destino.is_file():
            pasta.mkdir(parents=True, exist_ok=True)
            try:
                self._baixar_arquivo(url, destino.with_suffix(".tmp")).replace(destino)
            except Exception:  # sem imagem o app mostra a capa desenhada / as iniciais
                return None
        return destino

    # ----------------------------------------------------------------- conta

    def criar_conta(self, nome, email, senha):
        raise DadosInvalidos(f"Crie a conta no site: {self.site}/conta/nova")

    def entrar(self, email, senha):
        try:
            r = self._pedir("POST", "sessao", campos={"login": email, "senha": senha, "computador": self.computador})
        except LoginNecessario as e:
            raise CredenciaisInvalidas(str(e)) from None
        except SemPermissao as e:  # conta sem confirmar, excluida ou suspensa: o site explica
            raise CredenciaisInvalidas(str(e)) from None
        self._guardar_conta(r["conta"])
        return r["token"], self._conta(r["conta"])

    def sair(self, token):
        try:
            self._pedir("DELETE", "sessao", token)
        except Exception:
            pass
        (self.cache / "conta.json").unlink(missing_ok=True)

    def conta(self, token):
        if not token:
            return None
        try:
            dados = self._pedir("GET", "eu", token)
        except LoginNecessario:
            return None  # token revogado: o servico encerra a sessao
        except SemConexao:
            dados = self._conta_guardada()  # sem internet a pessoa continua logada
            if not dados:
                raise
        self._guardar_conta(dados)
        return self._conta(dados)

    def _guardar_conta(self, dados):
        self.cache.mkdir(parents=True, exist_ok=True)
        p = self.cache / "conta.json"
        p.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
        p.chmod(0o600)

    def _conta_guardada(self):
        try:
            return json.loads((self.cache / "conta.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _extras_do_perfil(self, d):
        """Banner, links e seguidores (o site manda desde a API com perfil completo; antes, ficam vazios)."""
        return {"banner": self._imagem(d.get("banner"), "banners", d["usuario"]),
                "localizacao": d.get("localizacao") or "", "site": d.get("site") or "",
                "github": d.get("github") or "", "seguidores": d.get("seguidores") or 0,
                "seguindo": d.get("seguindo") or 0, "pagina": d.get("perfil") or f"{self.site}/u/{d['usuario']}"}

    def _conta(self, d):
        return Conta(id=d["usuario"], nome=d["nome"], email=d.get("email", ""), criada_em=_data(d.get("criada_em")),
                     bio=d.get("bio") or "", foto=self._imagem(d.get("foto"), "fotos", d["usuario"]),
                     limites=d.get("limites") or {}, **self._extras_do_perfil(d))

    def atualizar_perfil(self, token, nome, email, bio, links=None):
        """O e-mail so muda pelo site (pede um codigo enviado para ele)."""
        atual = self._conta_guardada() or {}
        if email and email.strip().lower() != atual.get("email", "").lower():
            raise DadosInvalidos(f"Para trocar o e-mail, use o site (pede um código): {self.site}/conta/editar")
        campos = {"nome": nome, "bio": bio}
        campos.update({k: v for k, v in (links or {}).items() if k in ("localizacao", "site", "github")})
        return self._conta(self._pedir("PATCH", "eu", token, campos=campos))

    def definir_foto(self, token, imagem_png):
        if imagem_png:
            dados = self._pedir("PATCH", "eu", token, arquivos={"foto": (imagem_png, "foto.png", "image/png")})
        else:
            dados = self._pedir("PATCH", "eu", token, campos={"remover_foto": "1"})
        return self._conta(dados)

    def alterar_senha(self, token, atual, nova):
        raise DadosInvalidos(f"Troque a senha pelo site: {self.site}/conta/editar")

    # ---------------------------------------------------------------- skins

    def _item(self, d):
        pasta = self.cache / "galeria" / d["slug"]
        capa = self._imagem(d.get("capa"), Path("galeria") / d["slug"], "capa")
        if capa:  # o app mostra pasta/capa.png
            pasta.mkdir(parents=True, exist_ok=True)
            alvo = pasta / "capa.png"
            if not alvo.exists() or alvo.resolve() != capa.resolve():
                alvo.unlink(missing_ok=True)
                alvo.symlink_to(capa.name)
        return ItemGaleria(id=d["slug"], nome=d["nome"], autor_id=d["autor"]["usuario"], autor_nome=d["autor"]["nome"],
                           descricao=d.get("descricao") or "", publica=not d.get("privada"), oficial=bool(d.get("oficial")),
                           publicada_em=_data(d.get("publicada_em")), downloads=d.get("downloads", 0),
                           favoritos=d.get("favoritos", 0), tamanho=d.get("tamanho", 0),
                           pasta=pasta if capa else None,
                           extras={"pagina": d.get("pagina"),
                                   "download": d.get("download"), "versao": d.get("versao"),
                                   "tags": d.get("tags") or [], "atualizada_em": _data(d.get("atualizada_em"))})

    def galeria(self):
        quando, itens = self._galeria
        if time.monotonic() - quando < CACHE_DA_GALERIA:
            return list(itens)
        todos = []
        try:
            for pagina in range(PAGINAS_DA_GALERIA):
                skins = self._pedir("GET", f"skins?pagina={pagina}")["skins"]
                todos += [self._item(d) for d in skins]
                if len(skins) < 24:
                    break
        except SemConexao:
            return list(itens)  # mostra o que ja tinha (ou nada) em vez de travar a galeria
        self._galeria = (time.monotonic(), todos)
        return list(todos)

    def da_conta(self, token):
        return [self._item(d) for d in self._pedir("GET", "eu/skins", token)["skins"]]

    def item(self, item_id, token=None):
        return self._item(self._pedir("GET", f"skins/{self._slug(item_id)}", token))

    def baixar(self, item_id, token=None):
        slug = self._slug(item_id)
        pasta = self.cache / "baixadas"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{slug}.mintskins"
        self._baixar_arquivo(f"{self.site}/api/v1/skins/{slug}/baixar", destino, token)
        self._galeria = (0.0, self._galeria[1])  # o numero de downloads mudou
        return destino

    def enviar(self, token, pasta, meta, publica, item_id=None):
        pasta = Path(pasta)
        with tempfile.TemporaryDirectory() as tmp:
            pacote = Path(tmp, f"{pasta.name}.mintskins")
            with tarfile.open(pacote, "w:gz") as tar:
                tar.add(pasta, arcname=pasta.name)
            arquivos = {"pacote": (pacote, pacote.name, "application/gzip")}
            if meta.get("capa"):
                arquivos["capa"] = (meta["capa"], "capa.png", "image/png")
            campos = {"nome": meta.get("nome", ""), "descricao": meta.get("descricao", ""),
                      "privada": "0" if publica else "1"}
            if item_id:
                slug = self._slug(item_id)
                self._pedir("POST", f"skins/{slug}/versoes", token, campos={}, arquivos=arquivos, tempo=TEMPO_ENVIO)
                d = self._pedir("PATCH", f"skins/{slug}", token, campos=campos)
            else:
                d = self._pedir("POST", "skins", token, campos=campos, arquivos=arquivos, tempo=TEMPO_ENVIO)
        self._galeria = (0.0, self._galeria[1])
        return self._item(d)

    def definir_publica(self, token, item_id, publica):
        self._pedir("PATCH", f"skins/{self._slug(item_id)}", token, campos={"privada": "0" if publica else "1"})
        self._galeria = (0.0, self._galeria[1])

    def remover(self, token, item_id, senha=None):
        """Com a senha da conta a skin sai na hora (devolve None). Conta sem senha (so Google/GitHub):
        o site manda um codigo por e-mail e devolve a pagina para confirmar."""
        r = self._pedir("DELETE", f"skins/{self._slug(item_id)}", token, campos={"senha": senha or ""}) or {}
        self._galeria = (0.0, self._galeria[1])
        return None if r.get("removida") else r.get("confirmar")

    def favoritar(self, token, item_id, favorito):
        self._pedir("POST" if favorito else "DELETE", f"skins/{self._slug(item_id)}/favorito", token, campos={})
        self._galeria = (0.0, self._galeria[1])

    def favoritos(self, token):
        try:
            return set(self._pedir("GET", "eu/favoritos", token)["favoritos"])
        except (SemConexao, LoginNecessario):
            return set()

    def contagem_favoritos(self, item_id):
        slug = self._slug(item_id)
        return next((i.favoritos for i in self.galeria() if i.id == slug), 0)

    def perfil(self, autor_id):
        try:
            d = self._pedir("GET", f"perfis/{urllib.parse.quote(autor_id)}")
        except SkinNaoEncontrada:
            return None
        return Perfil(id=d["usuario"], nome=d["nome"], desde=_data(d.get("desde")), oficial=bool(d.get("oficial")),
                      itens=[self._item(s) for s in d.get("skins", [])], bio=d.get("bio") or "",
                      foto=self._imagem(d.get("foto"), "fotos", d["usuario"]), **self._extras_do_perfil(d))

    @staticmethod
    def _slug(item_id):
        """Skin oficial do app ("oficial:macos") e a mesma da conta oficial no site (slug "macos")."""
        return item_id[len(PREFIXO_OFICIAL):] if item_id.startswith(PREFIXO_OFICIAL) else item_id
