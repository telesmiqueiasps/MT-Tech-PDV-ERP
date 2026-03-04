import tkinter as tk
from datetime import date
from config import THEME, FONT
from core.session import Session


class Dashboard(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=THEME["bg"])
        self.pack(fill="both", expand=True, padx=28, pady=22)
        self._build()

    def _build(self):
        hora = __import__("datetime").datetime.now().hour
        saudacao = "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"

        tk.Label(self, text=f"{saudacao}, {Session.usuario()['login']}!",
                 font=("Segoe UI", 20, "bold"),
                 bg=THEME["bg"], fg=THEME["fg"]).pack(anchor="w")

        data = date.today().strftime("%d/%m/%Y")
        tk.Label(self, text=f"{Session.empresa()['nome']}  •  {data}",
                 font=FONT["sm"], bg=THEME["bg"],
                 fg=THEME["fg_light"]).pack(anchor="w", pady=(2, 24))

        # Cards só para usuários de empresa
        if not Session.is_admin_global():
            frame_cards = tk.Frame(self, bg=THEME["bg"])
            frame_cards.pack(fill="x")
            cards = self._stats()
            for i, c in enumerate(cards):
                self._card(frame_cards, c, col=i)
            for i in range(len(cards)):
                frame_cards.columnconfigure(i, weight=1)

        # Aviso admin global
        if Session.is_admin_global():
            aviso = tk.Frame(self, bg=THEME["bg_card"], padx=20, pady=14)
            aviso.pack(fill="x", pady=(0, 0))
            tk.Label(aviso, text="🔑  Você está logado como Administrador Global",
                     font=FONT["bold"], bg=THEME["bg_card"],
                     fg=THEME["primary"]).pack(anchor="w")
            tk.Label(aviso, text="Use o menu Administração para gerenciar empresas e usuários.",
                     font=FONT["sm"], bg=THEME["bg_card"],
                     fg=THEME["fg_light"]).pack(anchor="w")

    def _stats(self) -> list[dict]:
        try:
            from core.database import DatabaseManager
            db   = DatabaseManager.empresa()
            hoje = date.today().isoformat()
            vendas = db.fetchone(
                "SELECT COUNT(*) as total, COALESCE(SUM(total),0) as valor "
                "FROM vendas WHERE DATE(criado_em)=? AND status='FINALIZADA'", (hoje,)
            ) or {"total": 0, "valor": 0}
            produtos = db.fetchone(
                "SELECT COUNT(*) as total FROM produtos WHERE ativo=1"
            ) or {"total": 0}
            clientes = db.fetchone(
                "SELECT COUNT(*) as total FROM clientes WHERE ativo=1"
            ) or {"total": 0}
            estoque_baixo = db.fetchone(
                "SELECT COUNT(*) as total FROM produtos "
                "WHERE ativo=1 AND estoque_atual <= estoque_min AND estoque_min > 0"
            ) or {"total": 0}
        except Exception:
            vendas        = {"total": 0, "valor": 0}
            produtos      = {"total": 0}
            clientes      = {"total": 0}
            estoque_baixo = {"total": 0}

        return [
            {"icone": "🛒", "titulo": "Vendas Hoje",  "valor": str(vendas["total"]),
             "sub": f"R$ {vendas['valor']:,.2f}",      "cor": THEME["primary"]},
            {"icone": "📦", "titulo": "Produtos",      "valor": str(produtos["total"]),
             "sub": "cadastrados",                      "cor": THEME["success"]},
            {"icone": "👥", "titulo": "Clientes",      "valor": str(clientes["total"]),
             "sub": "ativos",                           "cor": "#8E44AD"},
            {"icone": "⚠",  "titulo": "Estoque Baixo", "valor": str(estoque_baixo["total"]),
             "sub": "produtos",                         "cor": THEME["warning"]},
        ]

    def _card(self, parent: tk.Frame, dados: dict, col: int):
        card = tk.Frame(parent, bg=THEME["bg_card"], padx=20, pady=16)
        card.grid(row=0, column=col, padx=(0, 14), sticky="nsew")

        topo = tk.Frame(card, bg=THEME["bg_card"])
        topo.pack(fill="x")
        tk.Label(topo, text=dados["icone"], font=("Segoe UI", 26),
                 bg=THEME["bg_card"]).pack(side="left")
        tk.Label(topo, text=dados["valor"], font=("Segoe UI", 28, "bold"),
                 bg=THEME["bg_card"], fg=dados["cor"]).pack(side="right")

        tk.Frame(card, bg=THEME["border"], height=1).pack(fill="x", pady=10)

        rodape = tk.Frame(card, bg=THEME["bg_card"])
        rodape.pack(fill="x")
        tk.Label(rodape, text=dados["titulo"], font=FONT["bold"],
                 bg=THEME["bg_card"], fg=THEME["fg"]).pack(side="left")
        tk.Label(rodape, text=dados["sub"], font=FONT["sm"],
                 bg=THEME["bg_card"], fg=THEME["fg_light"]).pack(side="right")