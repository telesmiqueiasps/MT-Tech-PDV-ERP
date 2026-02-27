"""
SearchEntry — campo de busca com dropdown de resultados em tempo real.
Substitui ttk.Combobox em buscas de fornecedores, clientes e produtos.

Uso:
    se = SearchEntry(parent, placeholder="Buscar fornecedor...",
                     items=lista_de_dicts,
                     key_display=lambda d: f"{d['nome']} — {d.get('cnpj','')}",
                     ao_selecionar=callback)
    se.pack(...)

    se.get_item()  → dict selecionado ou None
    se.set_item(dict)
    se.limpar()
"""
import tkinter as tk
from tkinter import ttk
from config import THEME, FONT


class SearchEntry(tk.Frame):
    """Campo de busca com lista dropdown filtrada em tempo real."""

    def __init__(self, master, placeholder="Buscar...",
                 items: list = None,
                 key_display=None,
                 key_search=None,
                 ao_selecionar=None,
                 max_resultados=80,
                 **kw):
        bg = THEME.get("bg_card", "#fff")
        super().__init__(master, bg=bg, **kw)

        self._items         = items or []
        self._key_display   = key_display or (lambda d: str(d))
        self._key_search    = key_search   or self._key_display
        self._ao_selecionar = ao_selecionar
        self._max           = max_resultados
        self._selected      = None
        self._popup         = None
        self._ignorar_trace = False

        # Entrada
        self._var = tk.StringVar()
        self._entry = tk.Entry(
            self, textvariable=self._var,
            font=FONT["md"],
            relief="flat",
            bg=THEME.get("bg", "white"),
            fg=THEME["fg"],
            insertbackground=THEME["fg"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["primary"],
        )
        self._entry.pack(fill="both", expand=True, ipady=5)

        # Placeholder
        self._placeholder = placeholder
        self._set_placeholder()

        self._entry.bind("<FocusIn>",    self._on_focus_in)
        self._entry.bind("<FocusOut>",   self._on_focus_out)
        self._entry.bind("<KeyRelease>", self._on_key)
        self._entry.bind("<Down>",       self._popup_focus_down)
        self._entry.bind("<Escape>",     self._fechar_popup)
        self._var.trace_add("write",     self._on_trace)

    # ── Placeholder ──────────────────────────────────────────────
    def _set_placeholder(self):
        self._var.set(self._placeholder)
        self._entry.configure(fg=THEME.get("fg_light", "#999"))
        self._is_placeholder = True

    def _clear_placeholder(self):
        if getattr(self, "_is_placeholder", False):
            self._ignorar_trace = True
            self._var.set("")
            self._ignorar_trace = False
            self._entry.configure(fg=THEME["fg"])
            self._is_placeholder = False

    def _on_focus_in(self, _=None):
        self._clear_placeholder()
        self._entry.configure(highlightbackground=THEME["primary"])
        self._mostrar_popup()

    def _on_focus_out(self, _=None):
        self._entry.configure(highlightbackground=THEME["border"])
        # Aguarda um momento para ver se o clique foi no popup
        self.after(150, self._check_fechar)

    def _check_fechar(self):
        if self._popup and self._popup.winfo_exists():
            try:
                focused = self.focus_get()
                if focused and str(focused).startswith(str(self._popup)):
                    return
            except Exception:
                pass
        self._fechar_popup()
        if not self._var.get() and not self._selected:
            self._set_placeholder()

    # ── Busca e popup ────────────────────────────────────────────
    def _on_trace(self, *_):
        if not self._ignorar_trace and not getattr(self, "_is_placeholder", False):
            self._mostrar_popup()

    def _on_key(self, event):
        if event.keysym in ("Return", "KP_Enter"):
            # Seleciona primeiro resultado
            if self._popup and self._popup.winfo_exists():
                children = [w for w in self._popup_list.winfo_children()
                            if isinstance(w, tk.Label)]
                if children:
                    children[0].event_generate("<Button-1>")
        elif event.keysym == "Escape":
            self._fechar_popup()

    def _popup_focus_down(self, _=None):
        if self._popup and self._popup.winfo_exists():
            children = [w for w in self._popup_list.winfo_children()
                        if isinstance(w, tk.Label)]
            if children:
                children[0].focus_set()

    def _mostrar_popup(self):
        busca = self._var.get().lower().strip()
        if getattr(self, "_is_placeholder", False):
            busca = ""

        # Filtra
        if busca:
            filtrados = [
                d for d in self._items
                if busca in self._key_search(d).lower()
            ][:self._max]
        else:
            filtrados = self._items[:self._max]

        self._fechar_popup(destruir=False)

        if not filtrados and busca:
            return

        # Posiciona popup abaixo do entry
        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.configure(bg=THEME["border"])

        self.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        w = max(self.winfo_width(), 280)
        self._popup.geometry(f"{w}x1+{x}+{y}")

        # Scroll container
        outer = tk.Frame(self._popup, bg=THEME["bg_card"],
                         highlightthickness=1,
                         highlightbackground=THEME["primary"])
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=THEME["bg_card"],
                           highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        max_h = min(len(filtrados) * 32 + 4, 280)
        canvas.configure(height=max_h)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._popup_list = tk.Frame(canvas, bg=THEME["bg_card"])
        win = canvas.create_window((0, 0), window=self._popup_list, anchor="nw")
        self._popup_list.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.bind("<Configure>",
            lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Atualiza tamanho real do popup
        self._popup.geometry(f"{w}x{max_h + 4}+{x}+{y}")

        for item in filtrados:
            lbl_txt = self._key_display(item)
            lbl = tk.Label(
                self._popup_list,
                text=lbl_txt,
                font=FONT["md"],
                bg=THEME["bg_card"],
                fg=THEME["fg"],
                anchor="w",
                padx=10, pady=5,
                cursor="hand2",
            )
            lbl.pack(fill="x")
            lbl.bind("<Enter>",
                lambda e, l=lbl: l.configure(
                    bg=THEME["primary"], fg="white"))
            lbl.bind("<Leave>",
                lambda e, l=lbl: l.configure(
                    bg=THEME["bg_card"], fg=THEME["fg"]))
            lbl.bind("<Button-1>",
                lambda e, d=item: self._selecionar(d))
            # Navegação por teclado no popup
            lbl.bind("<Down>",  self._nav_popup)
            lbl.bind("<Up>",    self._nav_popup)
            lbl.bind("<Return>",lambda e, d=item: self._selecionar(d))

    def _nav_popup(self, event):
        children = [w for w in self._popup_list.winfo_children()
                    if isinstance(w, tk.Label)]
        if not children:
            return
        try:
            idx = children.index(event.widget)
        except ValueError:
            return
        if event.keysym == "Down" and idx < len(children) - 1:
            children[idx + 1].focus_set()
        elif event.keysym == "Up":
            if idx > 0:
                children[idx - 1].focus_set()
            else:
                self._entry.focus_set()

    def _selecionar(self, item: dict):
        self._selected = item
        self._ignorar_trace = True
        self._var.set(self._key_display(item))
        self._ignorar_trace = False
        self._entry.configure(fg=THEME["fg"])
        self._is_placeholder = False
        self._fechar_popup()
        if self._ao_selecionar:
            self._ao_selecionar(item)

    def _fechar_popup(self, destruir=True, *_):
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

    # ── API pública ───────────────────────────────────────────────
    def get_item(self) -> dict | None:
        return self._selected

    def set_item(self, item: dict):
        self._selected = item
        self._ignorar_trace = True
        self._var.set(self._key_display(item) if item else "")
        self._ignorar_trace = False
        self._is_placeholder = not bool(item)
        if not item:
            self._set_placeholder()

    def set_items(self, items: list):
        self._items = items

    def limpar(self):
        self._selected = None
        self._set_placeholder()

    def get_text(self) -> str:
        if getattr(self, "_is_placeholder", False):
            return ""
        return self._var.get()

    def configure_state(self, state: str):
        self._entry.configure(state=state)