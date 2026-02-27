import tkinter as tk
from tkinter import ttk
from config import THEME, FONT


class PageHeader(tk.Frame):
    def __init__(self, master, icone: str, titulo: str, subtitulo: str = ""):
        super().__init__(master, bg=THEME["bg_card"],
                         highlightthickness=1,
                         highlightbackground=THEME["border"])
        faixa = tk.Frame(self, bg=THEME["primary"], width=5)
        faixa.pack(side="left", fill="y")

        conteudo = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=14)
        conteudo.pack(side="left", fill="both", expand=True)

        linha = tk.Frame(conteudo, bg=THEME["bg_card"])
        linha.pack(anchor="w")

        tk.Label(linha, text=icone, font=("Segoe UI", 22),
                 bg=THEME["bg_card"], fg=THEME["primary"]).pack(side="left", padx=(0, 10))

        textos = tk.Frame(linha, bg=THEME["bg_card"])
        textos.pack(side="left")
        tk.Label(textos, text=titulo, font=FONT["title"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w")
        if subtitulo:
            tk.Label(textos, text=subtitulo, font=FONT["sm"],
                     bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(anchor="w")


class SecaoForm(tk.Frame):
    def __init__(self, master, titulo: str):
        super().__init__(master, bg=THEME["section_bg"],
                         highlightthickness=1,
                         highlightbackground=THEME["primary_light"])
        tk.Label(self, text=f"  {titulo}", font=("Segoe UI", 9, "bold"),
                 bg=THEME["section_bg"], fg=THEME["section_fg"],
                 pady=6).pack(anchor="w")


class CampoEntry(tk.Frame):
    """
    Label + Entry em bloco vertical.
    Não passe bg — usa bg_card por padrão, ou passe bg_frame para customizar.
    """
    def __init__(self, master, label: str, var: tk.StringVar,
                 readonly: bool = False, show: str = "",
                 justify: str = "left", bg_frame: str = None):
        bg = bg_frame or THEME["bg_card"]
        super().__init__(master, bg=bg)
        tk.Label(self, text=label, font=FONT["sm"],
                 bg=bg, fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        estado = "readonly" if readonly else "normal"
        bg_entry = THEME["row_alt"] if readonly else THEME["bg_input"]
        self.entry = tk.Entry(self, textvariable=var, font=FONT["md"],
                              show=show, state=estado,
                              relief="flat", bg=bg_entry, fg=THEME["fg"],
                              justify=justify,
                              highlightthickness=1,
                              highlightbackground=THEME["border"],
                              highlightcolor=THEME["primary"],
                              disabledbackground=bg_entry,
                              disabledforeground=THEME["fg_light"])
        self.entry.pack(fill="x", ipady=7)


def botao(parent, texto: str, tipo: str = "primario", **kwargs) -> tk.Button:
    estilos = {
        "primario":   (THEME["primary"],     THEME["fg_white"]),
        "secundario": (THEME["bg_card"],      THEME["fg"]),
        "perigo":     (THEME["danger_light"], THEME["danger"]),
        "sucesso":    (THEME["success"],      THEME["fg_white"]),
        "ghost":      (THEME["bg"],           THEME["fg_light"]),
    }
    bg, fg = estilos.get(tipo, estilos["primario"])
    return tk.Button(parent, text=texto, font=FONT["bold"],
                     bg=bg, fg=fg, relief="flat", cursor="hand2",
                     activebackground=THEME["hover"],
                     activeforeground=THEME["fg"],
                     padx=14, pady=6, **kwargs)