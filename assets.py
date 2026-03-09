"""
Carrega e centraliza todos os assets visuais do sistema.
Uso:
    from assets import Assets
    Assets.init(root)               # chamar uma vez no main.py
    Assets.icon(janela)             # aplica logo.ico na janela
    Assets.logo()                   # retorna PhotoImage da logo.png
    Assets.logo_branca()            # retorna PhotoImage da logo_branca.png
"""
import tkinter as tk
from pathlib import Path

IMG_DIR = Path(__file__).resolve().parent / "img"


class Assets:
    _root:         tk.Tk | None = None
    _logo:         tk.PhotoImage | None = None
    _logo_branca:  tk.PhotoImage | None = None
    _ico_path:     str | None = None
    _icones_menu:  dict = {}   # cache: "nome_tamanho" → PhotoImage

    @classmethod
    def init(cls, root: tk.Tk):
        cls._root = root
        ico = IMG_DIR / "logo.ico"
        if ico.exists():
            cls._ico_path = str(ico)
            try:
                root.iconbitmap(cls._ico_path)
            except Exception:
                pass
            # Aplica ícone automaticamente em todos os Toplevel ao serem exibidos,
            # incluindo simpledialog e messagebox, sem precisar de acesso direto.
            ico_path = cls._ico_path
            def _auto_icon(event):
                try:
                    event.widget.iconbitmap(ico_path)
                except Exception:
                    pass
            root.bind_class("Toplevel", "<Map>", _auto_icon, add=True)

    @classmethod
    def icon(cls, janela: tk.Toplevel | tk.Tk):
        if cls._ico_path:
            try:
                janela.iconbitmap(cls._ico_path)
            except Exception:
                pass

    @classmethod
    def setup_toplevel(cls, janela: tk.Toplevel, largura: int, altura: int):
        """Aplica ícone, centraliza na tela e traz a janela para o foco."""
        cls.icon(janela)
        # Esconde temporariamente para evitar flash na posição padrão (0,0)
        janela.withdraw()
        janela.update_idletasks()
        sw = janela.winfo_screenwidth()
        sh = janela.winfo_screenheight()
        x = (sw - largura) // 2
        y = max(0, (sh - altura) // 2)
        janela.geometry("{}x{}+{}+{}".format(largura, altura, x, y))
        janela.deiconify()
        # No Windows focus_force sozinho não garante foco; -topmost temporário resolve
        janela.attributes("-topmost", True)
        janela.lift()
        janela.focus_force()
        janela.after(150, lambda: janela.attributes("-topmost", False))

    @classmethod
    def logo(cls, largura: int = None, altura: int = None) -> tk.PhotoImage | None:
        return cls._carregar("_logo", "logo.png", largura, altura)

    @classmethod
    def logo_branca(cls, largura: int = None, altura: int = None) -> tk.PhotoImage | None:
        return cls._carregar("_logo_branca", "logo_branca.png", largura, altura)

    @classmethod
    def icone_menu(cls, nome: str, tamanho: int = 18) -> tk.PhotoImage | None:
        """Carrega e cacheia um ícone da pasta img para uso nos botões do menu lateral."""
        key = f"{nome}_{tamanho}"
        if key in cls._icones_menu:
            return cls._icones_menu[key]
        caminho = IMG_DIR / f"{nome}.png"
        if not caminho.exists():
            return None
        try:
            from PIL import Image, ImageTk
            img = Image.open(caminho).convert("RGBA")
            img = img.resize((tamanho, tamanho), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            cls._icones_menu[key] = photo
            return photo
        except Exception:
            return None

    @classmethod
    def _carregar(cls, attr: str, nome: str,
                  largura: int = None, altura: int = None) -> tk.PhotoImage | None:
        caminho = IMG_DIR / nome
        if not caminho.exists():
            return None
        try:
            from PIL import Image, ImageTk
            img = Image.open(caminho)
            if largura and altura:
                img = img.resize((largura, altura), Image.LANCZOS)
            elif largura:
                ratio = largura / img.width
                img   = img.resize((largura, int(img.height * ratio)), Image.LANCZOS)
            elif altura:
                ratio = altura / img.height
                img   = img.resize((int(img.width * ratio), altura), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            setattr(cls, attr, photo)   # mantém referência para não ser coletado pelo GC
            return photo
        except Exception:
            return None