"""Repositorio de skins em disco (porta RepositorioSkins)."""
import json
import re
import shutil
import tarfile
import tempfile
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from ..dominio.erros import SkinInvalida, SkinSomenteLeitura
from ..dominio.skin import AUTOR_MINTSKINS, EXTENSAO, Origem, Skin
from .perfil import perfil_da_skin

_CAMPOS = {"id", "nome", "descricao", "autor", "criado_em", "atualizado_em", "dock", "baseada_em"}


def _data(texto):
    try:
        return datetime.fromisoformat(texto) if texto else None
    except ValueError:
        return None


def ler_meta(pasta):
    try:
        return json.loads(Path(pasta, "skin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def gravar_meta(pasta, meta):
    Path(pasta, "skin.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
                                        encoding="utf-8")


def skin_de_pasta(pasta, origem):
    pasta = Path(pasta)
    m = ler_meta(pasta)
    dock = m.get("dock")
    if dock is None:                      # pacote antigo do mac.sh: tem launchers = tem dock
        dock = (pasta / "plank/launchers").is_dir()
    return Skin(id=m.get("id") or pasta.name, nome=m.get("nome") or pasta.name, origem=origem,
                pasta=pasta, descricao=m.get("descricao", ""), autor=m.get("autor", ""),
                criado_em=_data(m.get("criado_em")), atualizado_em=_data(m.get("atualizado_em")),
                dock=bool(dock), baseada_em=m.get("baseada_em", ""),
                extras={k: v for k, v in m.items() if k not in _CAMPOS})


def meta_de_skin(skin):
    iso = lambda d: d.isoformat() if d else None
    m = dict(skin.extras)
    m.update(id=skin.id, nome=skin.nome, descricao=skin.descricao, autor=skin.autor,
             criado_em=iso(skin.criado_em), atualizado_em=iso(skin.atualizado_em),
             dock=skin.dock, versao=m.get("versao", 1))
    if skin.baseada_em:
        m["baseada_em"] = skin.baseada_em
    return m


class RepositorioArquivos:
    def __init__(self, pasta_usuario, pastas_mintskins, pasta_desfazer):
        self.usuario = Path(pasta_usuario)
        self.mintskins = [Path(p) for p in pastas_mintskins]
        self.pasta_desfazer = Path(pasta_desfazer)

    def listar(self):
        self.usuario.mkdir(parents=True, exist_ok=True)
        vistos, skins = set(), []
        fontes = [(p, Origem.MINTSKINS) for p in self.mintskins] + [(self.usuario, Origem.USUARIO)]
        for base, origem in fontes:
            for d in sorted(base.iterdir()):
                if d.is_dir() and not d.name.endswith(".novo") and perfil_da_skin(d):
                    s = skin_de_pasta(d, origem)
                    if s.id not in vistos:
                        vistos.add(s.id)
                        skins.append(s)
        return skins

    def novo_id(self, nome):
        s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
        s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "skin"
        base, i = s, 2
        while (self.usuario / s).exists() or any((p / s).exists() for p in self.mintskins):
            s = f"{base}-{i}"
            i += 1
        return s

    def _so_do_usuario(self, skin):
        # segunda barreira, alem da regra do dominio: nunca escrever nas incluidas
        if skin.incluida:
            raise SkinSomenteLeitura(f"“{skin.nome}” é uma skin padrão do MintSkins.")

    def gravar(self, skin, preencher=None, capa=None):
        self._so_do_usuario(skin)
        destino = self.usuario / skin.id
        if preencher:
            tmp = destino.with_name(destino.name + ".novo")
            if tmp.exists():
                shutil.rmtree(tmp)
            tmp.mkdir(parents=True)
            try:
                preencher(tmp)
                if capa:
                    shutil.copy2(capa, tmp / "capa.png")
                elif (destino / "capa.png").is_file():
                    shutil.copy2(destino / "capa.png", tmp / "capa.png")
                gravar_meta(tmp, meta_de_skin(skin))
            except BaseException:
                shutil.rmtree(tmp, ignore_errors=True)
                raise
            if destino.exists():
                shutil.rmtree(destino)
            tmp.rename(destino)
        else:
            destino.mkdir(parents=True, exist_ok=True)
            gravar_meta(destino, meta_de_skin(skin))
            if capa:
                shutil.copy2(capa, destino / "capa.png")
        skin.pasta = destino
        return skin

    def copiar(self, origem, nova):
        self._so_do_usuario(nova)
        destino = self.usuario / nova.id
        shutil.copytree(origem.pasta, destino, symlinks=True)
        if origem.incluida:
            (destino / "capa.png").unlink(missing_ok=True)
        gravar_meta(destino, meta_de_skin(nova))
        nova.pasta = destino
        return nova

    def excluir(self, skin):
        self._so_do_usuario(skin)
        shutil.rmtree(skin.pasta)

    def definir_capa(self, skin, imagem_png):
        self._so_do_usuario(skin)
        shutil.copy2(imagem_png, Path(skin.pasta) / "capa.png")

    def exportar(self, skin, arquivo):
        arquivo = str(arquivo)
        if not arquivo.endswith(EXTENSAO):
            arquivo += EXTENSAO
        with tarfile.open(arquivo, "w:gz") as tar:
            tar.add(skin.pasta, arcname=skin.id)
        return arquivo

    def importar(self, caminho, autor):
        """Arquivo .mintskins ou pasta (skin, ou o pacote/ do mac.sh). Vira skin do usuario."""
        caminho = Path(caminho)
        self.usuario.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=self.usuario.parent) as tmp:
            if caminho.is_dir():
                raiz = caminho
            else:
                try:
                    with tarfile.open(caminho, "r:*") as tar:
                        tar.extractall(tmp, filter="data")
                except (tarfile.TarError, OSError) as e:
                    raise SkinInvalida(f"Não foi possível abrir o arquivo: {e}") from e
                dirs = [d for d in Path(tmp).iterdir() if d.is_dir()]
                raiz = dirs[0] if len(dirs) == 1 and not perfil_da_skin(tmp) else Path(tmp)
            if not perfil_da_skin(raiz):
                raise SkinInvalida("Isto não é uma skin do MintSkins (falta perfil.conf).")
            skin = skin_de_pasta(raiz, Origem.USUARIO)
            if not ler_meta(raiz).get("nome"):
                skin.nome = caminho.stem.replace("_", " ").strip() or "Skin importada"
            if not skin.autor or skin.autor == AUTOR_MINTSKINS:
                skin.baseada_em = skin.baseada_em or skin.nome
                skin.autor = autor
            agora = datetime.now().replace(microsecond=0)
            skin.criado_em = skin.criado_em or agora
            skin.atualizado_em = skin.atualizado_em or skin.criado_em
            skin.id = self.novo_id(skin.nome)
            destino = self.usuario / skin.id
            shutil.copytree(raiz, destino, symlinks=True)
            if (destino / "perfil_mac.conf").exists() and not (destino / "perfil.conf").exists():
                (destino / "perfil_mac.conf").rename(destino / "perfil.conf")
            gravar_meta(destino, meta_de_skin(skin))
        skin.pasta = destino
        return skin

    def gravar_desfazer(self, preencher, estava_ativa):
        tmp = self.pasta_desfazer.with_name(self.pasta_desfazer.name + ".novo")
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        dock = preencher(tmp)
        gravar_meta(tmp, {"id": "desfazer", "nome": "Visual anterior", "estava_ativa": estava_ativa,
                          "criado_em": datetime.now().replace(microsecond=0).isoformat(),
                          "dock": bool(dock)})
        if self.pasta_desfazer.exists():
            shutil.rmtree(self.pasta_desfazer)
        tmp.rename(self.pasta_desfazer)

    def desfazer_disponivel(self):
        if perfil_da_skin(self.pasta_desfazer):
            return skin_de_pasta(self.pasta_desfazer, Origem.USUARIO)
        return None

    @contextmanager
    def desfazer_temporario(self):
        """Copia do 'desfazer' (o original e regravado durante a troca)."""
        tmp = self.pasta_desfazer.with_name(self.pasta_desfazer.name + ".aplicando")
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(self.pasta_desfazer, tmp, symlinks=True)
        try:
            yield skin_de_pasta(tmp, Origem.USUARIO)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
