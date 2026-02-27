"""
Widget de seleção de município com autocomplete.

Uso:
    widget = MunicipioWidget(parent)
    widget.pack(fill="x")

    # Ao selecionar, chama o callback com o dict do município
    widget.ao_selecionar = lambda m: print(m)

    # Preencher programaticamente (edição)
    widget.set_municipio("3550308", "São Paulo", "SP")

    # Ler valores
    cod  = widget.cod_municipio   # "3550308"
    nome = widget.nome_municipio  # "São Paulo"
    uf   = widget.uf              # "SP"
"""
import tkinter as tk
from tkinter import ttk
from config import THEME, FONT


class MunicipioWidget(tk.Frame):
    def __init__(self, master, label: str = "Município"):
        super().__init__(master, bg=THEME["bg_card"])
        self.ao_selecionar   = None
        self._municipio_selecionado = None
        self._apos_selecao   = False
        self._build(label)

    def _build(self, label: str):
        # Label principal
        tk.Label(self, text=label, font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))

        # Linha: UF | Campo de busca
        linha = tk.Frame(self, bg=THEME["bg_card"])
        linha.pack(fill="x")

        # Combo UF
        col_uf = tk.Frame(linha, bg=THEME["bg_card"], width=70)
        col_uf.pack(side="left", padx=(0, 6))
        col_uf.pack_propagate(False)
        tk.Label(col_uf, text="UF", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_uf = tk.StringVar()
        self._combo_uf = ttk.Combobox(col_uf, textvariable=self._var_uf,
                                       font=FONT["md"], width=4, state="readonly")
        self._combo_uf.pack(fill="x", ipady=4)
        self._combo_uf.bind("<<ComboboxSelected>>", self._on_uf_change)
        self._carregar_ufs()

        # Campo busca município
        col_mun = tk.Frame(linha, bg=THEME["bg_card"])
        col_mun.pack(side="left", fill="x", expand=True)
        tk.Label(col_mun, text="Cidade", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_busca = tk.StringVar()
        self._var_busca.trace_add("write", self._on_busca)
        self._entry = tk.Entry(col_mun, textvariable=self._var_busca,
                               font=FONT["md"], relief="flat",
                               bg=THEME["bg_input"], fg=THEME["fg"],
                               highlightthickness=1,
                               highlightbackground=THEME["border"],
                               highlightcolor=THEME["primary"])
        self._entry.pack(fill="x", ipady=7)

        # Código IBGE (readonly, preenchido automaticamente)
        col_cod = tk.Frame(linha, bg=THEME["bg_card"], width=100)
        col_cod.pack(side="left", padx=(6, 0))
        col_cod.pack_propagate(False)
        tk.Label(col_cod, text="Cód. IBGE", font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))
        self._var_cod = tk.StringVar()
        tk.Entry(col_cod, textvariable=self._var_cod, font=FONT["md"],
                 state="readonly", relief="flat",
                 bg=THEME["row_alt"], fg=THEME["fg_light"],
                 highlightthickness=1,
                 highlightbackground=THEME["border"],
                 justify="center").pack(fill="x", ipady=7)

        # Dropdown de resultados (inicialmente oculto)
        self._dropdown_frame = None

    def _carregar_ufs(self):
        try:
            from models.municipio import Municipio
            ufs = [""] + Municipio.ufs()
            self._combo_uf["values"] = ufs
            self._combo_uf.current(0)
        except Exception:
            pass

    def _on_uf_change(self, _=None):
        # Limpa seleção ao trocar UF
        self._municipio_selecionado = None
        self._var_cod.set("")
        self._fechar_dropdown()

    def _on_busca(self, *_):
        if self._apos_selecao:
            self._apos_selecao = False
            return
        termo = self._var_busca.get().strip()
        if len(termo) < 2:
            self._fechar_dropdown()
            return
        try:
            from models.municipio import Municipio
            uf       = self._var_uf.get().strip()
            resultados = Municipio.buscar(termo, uf)
            if resultados:
                self._abrir_dropdown(resultados)
            else:
                self._fechar_dropdown()
        except Exception:
            pass

    def _abrir_dropdown(self, resultados: list[dict]):
        self._fechar_dropdown()

        # Posiciona o dropdown abaixo do entry
        self._entry.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height()
        w = self._entry.winfo_width() + 106  # inclui col_cod

        top = tk.Toplevel(self)
        top.wm_overrideredirect(True)
        top.geometry(f"{w}x{min(len(resultados)*28+4, 280)}+{x}+{y}")
        top.configure(bg=THEME["border"])
        top.lift()

        frame = tk.Frame(top, bg="white")
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        scroll = ttk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(frame, font=FONT["md"],
                             bg="white", fg=THEME["fg"],
                             selectbackground=THEME["primary"],
                             selectforeground="white",
                             relief="flat", borderwidth=0,
                             activestyle="none",
                             yscrollcommand=scroll.set)
        scroll.configure(command=listbox.yview)
        listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._resultados_dropdown = resultados
        for m in resultados:
            listbox.insert("end", f"  {m['nome_municipio']} — {m['nome_uf']}")

        listbox.bind("<ButtonRelease-1>", lambda e: self._selecionar(listbox.curselection()))
        listbox.bind("<Return>",          lambda e: self._selecionar(listbox.curselection()))

        # Fecha ao clicar fora
        top.bind("<FocusOut>", lambda e: self._fechar_dropdown())
        self._entry.bind("<Escape>", lambda e: self._fechar_dropdown())
        self._entry.bind("<Down>",   lambda e: (listbox.focus_set(), listbox.selection_set(0)))

        self._dropdown_frame = top

    def _selecionar(self, selection):
        if not selection:
            return
        idx = selection[0]
        m   = self._resultados_dropdown[idx]
        self._apos_selecao = True
        self._var_busca.set(m["nome_municipio"])
        self._var_uf.set(m["uf"])
        self._var_cod.set(m["cod_municipio"])
        self._municipio_selecionado = m
        self._fechar_dropdown()
        if self.ao_selecionar:
            self.ao_selecionar(m)

    def _fechar_dropdown(self):
        if self._dropdown_frame:
            try:
                self._dropdown_frame.destroy()
            except Exception:
                pass
            self._dropdown_frame = None

    # ── API pública ──────────────────────────────────────────────

    def set_municipio(self, cod_municipio: str, nome: str = "", uf: str = ""):
        """Preenche o widget programaticamente (usado ao editar registro)."""
        if cod_municipio:
            try:
                from models.municipio import Municipio
                m = Municipio.buscar_por_codigo(cod_municipio)
                if m:
                    self._apos_selecao = True
                    self._var_busca.set(m["nome_municipio"])
                    self._var_uf.set(m["uf"])
                    self._var_cod.set(m["cod_municipio"])
                    self._municipio_selecionado = m
                    return
            except Exception:
                pass
        # Fallback: preenche com os valores passados diretamente
        self._var_busca.set(nome)
        self._var_uf.set(uf)
        self._var_cod.set(cod_municipio)

    @property
    def cod_municipio(self) -> str:
        return self._var_cod.get().strip()

    @property
    def nome_municipio(self) -> str:
        return self._var_busca.get().strip()

    @property
    def uf(self) -> str:
        return self._var_uf.get().strip()