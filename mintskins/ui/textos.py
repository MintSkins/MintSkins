"""Textos da interface."""

APP = "MintSkins"
SLOGAN = "Seu Linux Mint com a sua cara."
URL_PROJETO = "https://github.com/MintSkins/MintSkins"
PROPRIETARIO = "MintSkins"

SOBRE_NOS = (
    "O MintSkins deixa o Linux Mint com a sua cara, sem medo de estragar nada. "
    "Cada visual vira uma skin com nome, capa e autor: você troca com um clique "
    "e sempre consegue voltar.\n\n"
    "Acreditamos que personalizar o computador deve ser simples, seguro e bonito. "
    "Por isso o MintSkins guarda um backup antes da primeira troca, permite desfazer "
    "qualquer mudança e reúne skins oficiais e da comunidade numa galeria.")
LEGAL = ("© 2026 MintSkins. O nome MintSkins e o logotipo “m” são marcas do projeto MintSkins.\n"
         "Projeto independente, sem vínculo com o Linux Mint, a Apple ou os autores dos temas.")

NAV = {
    "inicio": ("go-home-symbolic", "Início"),
    "galeria": ("view-grid-symbolic", "Galeria"),
    "minhas": ("folder-symbolic", "Minhas skins"),
    "conta": ("avatar-default-symbolic", "Conta"),
    "preferencias": ("preferences-system-symbolic", "Preferências"),
    "sobre": ("help-about-symbolic", "Sobre"),
}

# (sobrelinha, titulo, frase) do topo de cada pagina
GALERIA = ("Galeria", "Explore skins", "Oficiais e da comunidade. Baixe, aplique e favorite as que você curtir.")
MINHAS = ("Neste computador", "Minhas skins", "Os visuais salvos aqui. Abra uma para aplicar, editar, publicar "
          "ou deixar privada.")
PREFERENCIAS = ("Ajustes", "Preferências", None)

FILTROS = [("todas", "Todas"), ("oficiais", "Oficiais"), ("comunidade", "Comunidade"),
           ("favoritas", "Favoritas")]
ORDENS = [("populares", "Populares"), ("recentes", "Mais recentes"), ("favoritadas", "Mais favoritadas")]
FILTROS_MINHAS = [("todas", "Todas"), ("publica", "Públicas"), ("privada", "Privadas"),
                  ("local", "Só neste computador")]

# onde uma skin sua fica: (chave, icone, titulo, explicacao)
ONDE = [
    ("local", "computer-symbolic", "Só neste computador", "Ninguém mais vê. Fica só aqui."),
    ("privada", "changes-prevent-symbolic", "Privada na conta",
     "Só você vê. Baixe em outro computador quando quiser."),
    ("publica", "web-browser-symbolic", "Pública na galeria",
     "Todo mundo vê no app e no site, pode baixar e favoritar."),
]

EM_USO = "Em uso agora"
SEM_BACKUP_TITULO = "Visual sem backup"
SEM_BACKUP_TEXTO = "Este visual ainda não foi salvo. Salve para poder voltar a ele."
AVISO_BACKUP_TITULO = "Salve seu visual antes da primeira troca"
AVISO_BACKUP_TEXTO = "Assim você sempre consegue voltar para ele."
OFICIAL_SOMENTE_LEITURA = "Skin oficial · não pode ser editada"

VAZIO_MINHAS = ("Nenhuma skin salva ainda", "Salve o visual atual ou baixe uma da galeria.")
VAZIO_FILTRO_MINHAS = {
    "publica": ("Nenhuma skin pública", "Abra uma skin e escolha Pública na galeria para todo mundo ver."),
    "privada": ("Nenhuma skin privada", "Abra uma skin e escolha Privada na conta para guardar só para você."),
    "local": ("Nenhuma skin só aqui", "Todas as suas skins estão na sua conta."),
    "busca": ("Nada encontrado", "Tente outro nome."),
}
VAZIO_GALERIA = ("Nada por aqui", "Tente outra busca ou outro filtro.")
VAZIO_FAVORITAS = ("Nenhuma favorita", "Toque no coração de uma skin para guardá-la aqui.")
VAZIO_NUVEM = ("Nada na sua conta", "Abra uma skin em Minhas skins e escolha onde ela fica.")

NUVEM_LOCAL = ("Sua conta é a mesma do mintskins.com: as skins que você envia ficam lá e "
               "aparecem na galeria do site e do app.")

SALVAR = "Salvar skin"
DESFAZER = "Desfazer a última troca"

PREF_APLICAR = [
    ("papel_de_parede", "Trocar o papel de parede", "Usa o papel de parede da skin."),
    ("recarregar", "Recarregar o Cinnamon", "O painel muda na hora; a tela pisca por um instante."),
    ("tela_login", "Aplicar na tela de login", "Pede a senha de administrador."),
]
PREF_TEMA = ("Tema do aplicativo", "Automático segue o tema do sistema.")
APARENCIAS = [("auto", "Automático"), ("clara", "Claro"), ("escura", "Escuro")]
