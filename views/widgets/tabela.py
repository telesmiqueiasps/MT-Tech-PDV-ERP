import tkinter as tk
from tkinter import ttk
from config import THEME, FONT


class Tabela(tk.Frame):
    def __init__(self, master, colunas: list[tuple[str, int]]):
        super().__init__(master, bg=THEME["bg_card"],
                         highlightthickness=1,
                         highlightbackground=THEME["border"])
        self.ao_selecionar   = None
        self.ao_duplo_clique = None
        self._build(colunas)

    def _build(self, colunas: list[tuple[str, int]]):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Tabela.Treeview",
                        background=THEME["bg_card"],
                        foreground=THEME["fg"],
                        rowheight=34,
                        fieldbackground=THEME["bg_card"],
                        font=FONT["md"],
                        borderwidth=0,
                        relief="flat")

        style.configure("Tabela.Treeview.Heading",
                        background=THEME["primary_dark"],
                        foreground=THEME["fg_white"],
                        font=FONT["bold"],
                        relief="flat",
                        borderwidth=0,
                        padding=(10, 8))

        style.map("Tabela.Treeview",
                  background=[("selected", THEME["primary"])],
                  foreground=[("selected", THEME["fg_white"])])

        style.map("Tabela.Treeview.Heading",
                  background=[("active", THEME["primary"])])

        ids = [c[0] for c in colunas]
        self._tree = ttk.Treeview(self, columns=ids, show="headings",
                                   style="Tabela.Treeview", selectmode="browse")

        for nome, largura in colunas:
            self._tree.heading(nome, text=nome)
            self._tree.column(nome, width=largura, minwidth=40, anchor="w")

        scroll_y = ttk.Scrollbar(self, orient="vertical",   command=self._tree.yview)
        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=scroll_y.set,
                              xscrollcommand=scroll_x.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tree.tag_configure("par",   background=THEME["bg_card"])
        self._tree.tag_configure("impar", background=THEME["row_alt"])

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-Button-1>",  self._on_duplo)

    def inserir(self, valores: list, tag: str = None):
        idx = len(self._tree.get_children())
        t   = tag or ("par" if idx % 2 == 0 else "impar")
        self._tree.insert("", "end", values=valores, tags=(t,))

    def limpar(self):
        self._tree.delete(*self._tree.get_children())

    def selecionado_indice(self) -> int | None:
        sel = self._tree.selection()
        if not sel:
            return None
        children = self._tree.get_children()
        try:
            return list(children).index(sel[0])
        except ValueError:
            return None

    def selecionado(self) -> list | None:
        sel = self._tree.selection()
        return list(self._tree.item(sel[0], "values")) if sel else None

    def _on_select(self, _=None):
        if self.ao_selecionar and self.selecionado():
            self.ao_selecionar(self.selecionado())

    def _on_duplo(self, _=None):
        if self.ao_duplo_clique and self.selecionado():
            self.ao_duplo_clique(self.selecionado())