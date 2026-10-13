"""Linha de comando: `mintskins` sem argumentos abre a janela."""
import sys

from . import __version__
from .composicao import montar
from .dominio.erros import BackupNecessario, MintSkinsErro
from .dominio.skin import EXTENSOES_ACEITAS

AJUDA = """MintSkins {v} — troque o visual do Linux Mint Cinnamon

  mintskins                      abre a interface grafica
  mintskins listar               lista as skins
  mintskins aplicar <skin>       aplica uma skin (id ou nome)
  mintskins salvar "<nome>"      salva o visual atual como skin
  mintskins desfazer             volta ao visual anterior a ultima troca
  mintskins atualizar            procura e instala uma versao nova
  mintskins exportar <skin> <arquivo.mintskins>
  mintskins importar <arquivo.mintskins | pasta>
  mintskins --segundo-plano      abre so o icone perto do relogio
  mintskins --version
"""


def _progresso(texto, fracao=None):
    pct = f"{round(fracao * 100):3d}% " if fracao is not None else "     "
    print(f"  {pct}{texto}")


def main(argv):
    app = montar()
    servico = app.skins
    if not argv or argv[0].endswith(EXTENSOES_ACEITAS) or argv == ["--segundo-plano"]:
        # sem argumentos, "abrir com" um .mintskins, ou o inicio junto com o sistema
        from .ui.app import main as gui
        oculto = argv == ["--segundo-plano"]
        return gui(app, [sys.argv[0], *([] if oculto else argv)], oculto=oculto)
    cmd, args = argv[0], argv[1:]
    if cmd in ("-h", "--help", "ajuda"):
        print(AJUDA.format(v=__version__))
        return 0
    if cmd in ("-v", "--version"):
        print(__version__)
        return 0
    try:
        servico.migrar_legado()
        if cmd == "listar":
            ativa = servico.ativa()
            for titulo, lista in (("Incluídas no MintSkins", servico.incluidas()),
                                  ("Minhas skins", servico.do_usuario())):
                print(f"{titulo}:")
                for s in lista:
                    marca = "*" if ativa and s.id == ativa.id else " "
                    quando = s.atualizado_em.strftime("%d/%m/%Y %H:%M") if s.atualizado_em else ""
                    print(f" {marca} {s.id:<24} {s.nome:<28} por {s.responsavel:<18} {quando}")
                if not lista:
                    print("   (nenhuma)")
        elif cmd == "aplicar" and len(args) == 1:
            s = servico.obter(args[0])
            print(f"Aplicando {s.nome}")
            for a in servico.aplicar(s, progresso=_progresso).avisos:
                print("  aviso: " + a)
        elif cmd == "salvar" and len(args) >= 1:
            s = servico.salvar_atual(args[0], " ".join(args[1:]), progresso=_progresso)
            print(f"Salva: {s.id}")
        elif cmd == "atualizar":
            nova = app.atualizacoes.verificar(forcar=True)
            if not nova:
                print(f"Você já tem a versão mais recente ({__version__}).")
            else:
                print(f"Nova versão: {nova.versao}\n{nova.pagina}")
                if nova.pacote_url and input("Instalar agora? [s/N] ").strip().lower() == "s":
                    app.atualizacoes.atualizar(nova)
                    print("Atualizado.")
        elif cmd == "desfazer":
            servico.desfazer(progresso=_progresso)
        elif cmd == "exportar" and len(args) == 2:
            print(servico.exportar(servico.obter(args[0]), args[1]))
        elif cmd == "importar" and len(args) == 1:
            s = servico.importar(args[0])
            print(f"Importada: {s.id} ({s.nome})")
        else:
            print(AJUDA.format(v=__version__))
            return 1
    except BackupNecessario as e:
        print(f"erro: {e}\n  rode antes: mintskins salvar \"Meu visual original\"", file=sys.stderr)
        return 1
    except MintSkinsErro as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0
