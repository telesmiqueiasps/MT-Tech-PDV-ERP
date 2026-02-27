"""
DateEntry — campo de data com formato DD/MM/AAAA.
Auto-insere as barras enquanto o usuário digita.
Mostra mini-calendário ao clicar no ícone.
"""
import tkinter as tk
from tkinter import ttk
import calendar
import datetime
from config import THEME, FONT


def _hoje() -> datetime.date:
    return datetime.date.today()


def _parse(texto: str) -> datetime.date | None:
    """Tenta converter DD/MM/AAAA ou AAAA-MM-DD para date."""
    t = texto.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d%m%Y"):
        try:
            return datetime.datetime.strptime(t, fmt).date()
        except ValueError:
            continue
    return None


def _fmt(d: datetime.date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else ""


class DateEntry(tk.Frame):
    """
    Campo de data com máscara DD/MM/AAAA.

    Uso:
        de = DateEntry(parent, label="Data Entrada")
        de.pack(...)
        de.get()       → "2025-02-26"  (ISO, pronto para BD)
        de.get_br()    → "26/02/2025"  (exibição)
        de.set("2025-02-26")  ou  de.set("26/02/2025")
    """
    def __init__(self, master, label: str = "", value: str = "",
                 width: int = 12, **kw):
        bg = THEME.get("bg_card", "#fff")
        super().__init__(master, bg=bg, **kw)

        if label:
            tk.Label(self, text=label, font=FONT["sm"],
                     bg=bg, fg=THEME["fg"]).pack(anchor="w", pady=(0, 3))

        row = tk.Frame(self, bg=bg)
        row.pack(fill="x")

        self._var = tk.StringVar()
        self._entry = tk.Entry(
            row, textvariable=self._var, font=FONT["md"],
            width=width, relief="flat",
            bg=THEME.get("bg", "white"), fg=THEME["fg"],
            insertbackground=THEME["fg"],
            highlightthickness=1,
            highlightbackground=THEME["border"],
            highlightcolor=THEME["primary"],
        )
        self._entry.pack(side="left", ipady=5)

        btn_cal = tk.Label(
            row, text="📅", font=("Segoe UI", 11),
            bg=bg, fg=THEME["primary"], cursor="hand2"
        )
        btn_cal.pack(side="left", padx=(4, 0))
        btn_cal.bind("<Button-1>", self._abrir_calendario)

        self._var.trace_add("write", self._mascara)
        self._digitando = False

        if value:
            self.set(value)

    # ── Máscara automática ───────────────────────────────────────
    def _mascara(self, *_):
        if self._digitando:
            return
        self._digitando = True
        raw = self._var.get()

        # Remove tudo que não é dígito
        digits = "".join(c for c in raw if c.isdigit())[:8]

        # Monta DD/MM/AAAA progressivamente
        out = ""
        for i, ch in enumerate(digits):
            out += ch
            if i == 1 or i == 3:
                out += "/"

        # Só atualiza se mudou para evitar loop
        cur = self._var.get()
        if out != cur:
            pos = self._entry.index(tk.INSERT)
            self._var.set(out)
            # Reposiciona cursor de forma inteligente
            new_pos = min(pos + (1 if len(out) > len(cur) and out[pos-1:pos] == "/" else 0), len(out))
            try:
                self._entry.icursor(new_pos)
            except Exception:
                pass

        self._digitando = False

    # ── Calendário popup ─────────────────────────────────────────
    def _abrir_calendario(self, event=None):
        # Determina data inicial
        d = _parse(self._var.get()) or _hoje()
        CalendarioPopup(self, data_inicial=d, ao_selecionar=self._on_cal_select)

    def _on_cal_select(self, d: datetime.date):
        self._var.set(_fmt(d))

    # ── API pública ───────────────────────────────────────────────
    def get(self) -> str:
        """Retorna AAAA-MM-DD para gravar no BD, ou '' se inválido."""
        d = _parse(self._var.get())
        return d.isoformat() if d else ""

    def get_br(self) -> str:
        """Retorna DD/MM/AAAA para exibição."""
        return self._var.get()

    def set(self, valor: str):
        """Aceita AAAA-MM-DD ou DD/MM/AAAA."""
        if not valor:
            self._var.set("")
            return
        d = _parse(valor)
        self._var.set(_fmt(d) if d else valor)

    def valido(self) -> bool:
        return _parse(self._var.get()) is not None

    def configure_state(self, state: str):
        self._entry.configure(state=state)


class CalendarioPopup(tk.Toplevel):
    """Mini-calendário mensal para seleção de data."""
    def __init__(self, master, data_inicial: datetime.date = None,
                 ao_selecionar=None):
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(bg=THEME["bg_card"])
        self.resizable(False, False)

        self._data   = data_inicial or _hoje()
        self._sel    = data_inicial
        self._cb     = ao_selecionar
        self._mes    = self._data.month
        self._ano    = self._data.year

        self._build()
        self._posicionar(master)

        # Fecha ao clicar fora
        self.bind("<FocusOut>", lambda e: self.destroy())
        self.focus_force()

    def _posicionar(self, master):
        try:
            x = master.winfo_rootx()
            y = master.winfo_rooty() + master.winfo_height()
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        bg   = THEME["bg_card"]
        prim = THEME["primary"]
        fg   = THEME["fg"]

        # Cabeçalho mês/ano
        hdr = tk.Frame(self, bg=prim, padx=4, pady=4)
        hdr.pack(fill="x")

        tk.Button(hdr, text="◀", font=FONT["sm"], bg=prim, fg="white",
                  bd=0, activebackground=THEME.get("primary_dark", prim),
                  activeforeground="white", cursor="hand2",
                  command=self._mes_anterior).pack(side="left")
        tk.Label(hdr,
                 text=f"{calendar.month_name[self._mes].capitalize()} {self._ano}",
                 font=FONT["bold"], bg=prim, fg="white").pack(side="left", expand=True)
        tk.Button(hdr, text="▶", font=FONT["sm"], bg=prim, fg="white",
                  bd=0, activebackground=THEME.get("primary_dark", prim),
                  activeforeground="white", cursor="hand2",
                  command=self._mes_proximo).pack(side="right")

        # Dias da semana
        dias_sem = tk.Frame(self, bg=bg, padx=4, pady=2)
        dias_sem.pack(fill="x")
        for i, d in enumerate(["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"]):
            tk.Label(dias_sem, text=d, font=("Segoe UI", 8, "bold"),
                     bg=bg, fg=THEME["fg_light"], width=3).grid(row=0, column=i, padx=1)

        # Grid de dias
        grid = tk.Frame(self, bg=bg, padx=4, pady=4)
        grid.pack()

        hoje = _hoje()
        cal  = calendar.monthcalendar(self._ano, self._mes)
        for row, semana in enumerate(cal):
            for col, dia in enumerate(semana):
                if dia == 0:
                    tk.Label(grid, text="", width=3, bg=bg).grid(row=row, column=col, padx=1, pady=1)
                    continue
                d = datetime.date(self._ano, self._mes, dia)
                is_hoje = d == hoje
                is_sel  = d == self._sel

                if is_sel:
                    bg_btn, fg_btn = prim, "white"
                elif is_hoje:
                    bg_btn, fg_btn = THEME.get("bg", "#f0f0f0"), prim
                else:
                    bg_btn, fg_btn = bg, fg

                btn = tk.Button(
                    grid, text=str(dia), font=FONT["sm"],
                    width=3, relief="flat", cursor="hand2",
                    bg=bg_btn, fg=fg_btn,
                    activebackground=prim, activeforeground="white",
                )
                if is_hoje and not is_sel:
                    btn.configure(font=("Segoe UI", 9, "bold"))
                btn.configure(command=lambda _d=d: self._selecionar(_d))
                btn.grid(row=row, column=col, padx=1, pady=1)

        # Botão Hoje
        rod = tk.Frame(self, bg=bg, pady=4)
        rod.pack(fill="x")
        tk.Button(rod, text="Hoje", font=FONT["sm"],
                  bg=THEME.get("bg", "#f0f0f0"), fg=prim,
                  relief="flat", cursor="hand2",
                  command=lambda: self._selecionar(_hoje())
                  ).pack()

    def _mes_anterior(self):
        if self._mes == 1:
            self._mes, self._ano = 12, self._ano - 1
        else:
            self._mes -= 1
        self._build()

    def _mes_proximo(self):
        if self._mes == 12:
            self._mes, self._ano = 1, self._ano + 1
        else:
            self._mes += 1
        self._build()

    def _selecionar(self, d: datetime.date):
        self._sel = d
        if self._cb:
            self._cb(d)
        self.destroy()