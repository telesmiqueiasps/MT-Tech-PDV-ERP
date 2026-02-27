import tkinter as tk
from tkinter import messagebox
from config import THEME, FONT


class BaseView(tk.Toplevel):
    def __init__(self, master, titulo: str = "", largura: int = 800,
                 altura: int = 600, modal: bool = True):
        super().__init__(master)
        self.title(titulo)
        self.configure(bg=THEME["bg"])
        self.resizable(True, True)
        self.lift()
        self.focus_force()
        self._centralizar(largura, altura)
        if modal:
            self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        try:
            from assets import Assets
            Assets.icon(self)
        except Exception:
            pass

    def _centralizar(self, largura: int, altura: int):
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - largura) // 2
        y = (self.winfo_screenheight() - altura)  // 2
        self.geometry(f"{largura}x{altura}+{x}+{y}")

    def _ao_fechar(self):
        self.destroy()

    def erro(self, msg: str):
        messagebox.showerror("Erro", msg, parent=self)

    def sucesso(self, msg: str):
        messagebox.showinfo("Sucesso", msg, parent=self)

    def confirmar(self, pergunta: str) -> bool:
        return messagebox.askyesno("Confirmar", pergunta, parent=self)