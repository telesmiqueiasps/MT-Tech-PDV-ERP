"""
Servidor Flask embutido para o app web de garçons.
Sobe em thread daemon na porta 5000 junto com o PDV.
"""
import threading
import datetime
import secrets
from pathlib import Path
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, redirect
from flask_cors import CORS

# ── Constantes ────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).resolve().parent / "garcom_templates"
IMG_DIR_PDV   = Path(__file__).resolve().parent.parent / "img"

# ── Estado em memória ─────────────────────────────────────────
_tokens: dict[str, dict] = {}        # token → {user_id, login, nome, exp}
_novos_pedidos: list[dict] = []      # notificações pendentes
_lock = threading.Lock()
_empresa_nome: str = ""

# ── App Flask ─────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)


# ── Auth helpers ──────────────────────────────────────────────
def _gerar_token(user: dict) -> str:
    token = secrets.token_urlsafe(32)
    exp = datetime.datetime.utcnow() + datetime.timedelta(hours=12)
    with _lock:
        _tokens[token] = {
            "user_id": user["id"],
            "login":   user["login"],
            "nome":    user.get("nome") or user["login"],
            "exp":     exp,
        }
    return token


def _verificar_token(token: str) -> dict | None:
    with _lock:
        info = _tokens.get(token)
    if not info:
        return None
    if datetime.datetime.utcnow() > info["exp"]:
        with _lock:
            _tokens.pop(token, None)
        return None
    return info


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Token requerido"}), 401
        user = _verificar_token(auth[7:])
        if not user:
            return jsonify({"error": "Token inválido ou expirado"}), 401
        request.garcom = user
        return f(*args, **kwargs)
    return decorated


# ── Rotas ─────────────────────────────────────────────────────
@app.route("/")
def root():
    return redirect("/garcom/")


@app.route("/garcom/")
def index():
    return send_from_directory(str(TEMPLATES_DIR), "app.html")


@app.route("/cozinha/")
def cozinha():
    return send_from_directory(str(TEMPLATES_DIR), "cozinha.html")


@app.route("/api/cozinha/itens")
def api_cozinha_itens():
    """Retorna itens pendentes e em preparo — sem auth (display interno)."""
    try:
        from core.database import DatabaseManager
        db   = DatabaseManager.empresa()
        rows = db.fetchall("""
            SELECT pi.id, pi.pedido_id, pi.produto_nome, pi.quantidade, pi.obs,
                   pi.status, pi.criado_em,
                   m.numero AS mesa_numero, m.nome AS mesa_nome, m.setor AS mesa_setor,
                   p.garcom_nome
            FROM pedido_itens pi
            JOIN pedidos p ON p.id = pi.pedido_id
            JOIN mesas   m ON m.id = p.mesa_id
            WHERE p.status = 'ABERTO'
              AND pi.status IN ('PENDENTE', 'EM_PREPARO')
            ORDER BY pi.criado_em ASC
        """)
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cozinha/item/<int:item_id>/status", methods=["PUT"])
def api_cozinha_item_status(item_id):
    """Atualiza status de um item (PENDENTE → EM_PREPARO → PRONTO)."""
    data = request.get_json() or {}
    novo = data.get("status", "")
    if novo not in ("PENDENTE", "EM_PREPARO", "PRONTO"):
        return jsonify({"error": "Status inválido"}), 400
    try:
        from core.database import DatabaseManager
        DatabaseManager.empresa().execute(
            "UPDATE pedido_itens SET status=? WHERE id=?", (novo, item_id))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/garcom/logo.png")
def logo_png():
    for nome in ["logo.png", "logo_branca.png"]:
        if (IMG_DIR_PDV / nome).exists():
            return send_from_directory(str(IMG_DIR_PDV), nome)
    return "", 404


@app.route("/garcom/manifest.json")
def manifest_json():
    nome = _empresa_nome or "MT Tech Garçom"
    return jsonify({
        "name": nome,
        "short_name": "Garçom",
        "start_url": "/garcom/",
        "display": "standalone",
        "background_color": "#2c78ac",
        "theme_color": "#2c78ac",
        "icons": [
            {"src": "/garcom/logo.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/garcom/logo.png", "sizes": "512x512", "type": "image/png"},
        ],
    })


@app.route("/garcom/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/info")
def api_info():
    return jsonify({
        "empresa": _empresa_nome or "MT Tech Garçom",
        "tem_logo": (IMG_DIR_PDV / "logo.png").exists(),
    })


@app.route("/api/login", methods=["POST"])
def api_login():
    data  = request.get_json() or {}
    login = data.get("login", "").strip()
    senha = data.get("senha", "")
    if not login or not senha:
        return jsonify({"error": "Login e senha obrigatórios"}), 400
    try:
        from core.database import DatabaseManager
        from core.auth import verificar_senha
        db  = DatabaseManager.empresa()
        row = db.fetchone(
            "SELECT u.*, p.nome AS perfil_nome FROM usuarios u "
            "LEFT JOIN perfis p ON p.id=u.perfil_id "
            "WHERE u.login=? AND u.ativo=1", (login,))
        if not row or not verificar_senha(senha, row["senha_hash"]):
            return jsonify({"error": "Login ou senha inválidos"}), 401
        token = _gerar_token(dict(row))
        return jsonify({"token": token,
                        "nome":  row.get("nome") or row["login"],
                        "login": row["login"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mesas")
@require_auth
def api_mesas():
    try:
        from models.mesa import Mesa
        mesas  = Mesa.listar(so_ativas=True)
        result = []
        for m in mesas:
            pedido = Mesa.pedido_aberto(m["id"])
            result.append({
                "id":        m["id"],
                "numero":    m["numero"],
                "nome":      m["nome"],
                "setor":     m.get("setor") or "Salão",
                "status":    m["status"],
                "capacidade":m.get("capacidade", 4),
                "pedido_id": pedido["id"]    if pedido else None,
                "total":     float(pedido["total"] or 0) if pedido else 0.0,
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mesa/<int:mesa_id>/abrir", methods=["POST"])
@require_auth
def api_abrir_mesa(mesa_id):
    try:
        from models.mesa import Mesa, Pedido
        pedido = Mesa.pedido_aberto(mesa_id)
        if pedido:
            return jsonify({"pedido_id": pedido["id"]})
        data    = request.get_json() or {}
        pessoas = int(data.get("pessoas", 1))
        user    = request.garcom
        pid = Pedido.abrir(
            mesa_id=mesa_id,
            garcom_id=user["user_id"],
            garcom_nome=user["nome"],
            pessoas=pessoas,
        )
        return jsonify({"pedido_id": pid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pedido/<int:pedido_id>/itens")
@require_auth
def api_pedido_itens(pedido_id):
    try:
        from models.mesa import Pedido
        ped = Pedido.buscar_por_id(pedido_id)
        if not ped:
            return jsonify({"error": "Pedido não encontrado"}), 404
        itens = Pedido.itens(pedido_id)
        return jsonify({
            "pedido": dict(ped),
            "itens":  [dict(i) for i in itens],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pedido/<int:pedido_id>/item", methods=["POST"])
@require_auth
def api_adicionar_item(pedido_id):
    try:
        from models.mesa import Pedido
        from models.produto import Produto
        data       = request.get_json() or {}
        produto_id = int(data.get("produto_id", 0))
        quantidade = float(data.get("quantidade", 1))
        obs        = data.get("obs", "")
        if not produto_id:
            return jsonify({"error": "produto_id obrigatório"}), 400
        produto = Produto.buscar_por_id(produto_id)
        if not produto:
            return jsonify({"error": "Produto não encontrado"}), 404
        from models.estoque import Estoque
        saldo = Estoque.saldo_total_produto(produto_id)
        if saldo <= 0:
            return jsonify({"error": f"Produto '{produto['nome']}' sem estoque disponível."}), 409
        if quantidade > saldo:
            return jsonify({"error": f"Estoque insuficiente. Disponível: {saldo:g} {produto.get('unidade','UN')}."}), 409
        iid = Pedido.adicionar_item(pedido_id, dict(produto), quantidade, obs)
        # Notificação para popup no PDV
        user = request.garcom
        ped  = Pedido.buscar_por_id(pedido_id)
        with _lock:
            _novos_pedidos.append({
                "pedido_id":    pedido_id,
                "item_id":      iid,
                "mesa_id":      ped["mesa_id"] if ped else None,
                "mesa_numero":  None,   # resolvido no popup
                "produto_nome": produto["nome"],
                "quantidade":   quantidade,
                "garcom_nome":  user["nome"],
                "hora":         datetime.datetime.now().strftime("%H:%M"),
            })
        return jsonify({"item_id": iid})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/item/<int:item_id>", methods=["DELETE"])
@require_auth
def api_remover_item(item_id):
    try:
        from models.mesa import Pedido
        Pedido.remover_item(item_id)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pedido/<int:pedido_id>/prontos")
@require_auth
def api_pedido_prontos(pedido_id):
    """Retorna itens com status PRONTO do pedido — para notificar o garçom."""
    try:
        from core.database import DatabaseManager
        rows = DatabaseManager.empresa().fetchall(
            "SELECT id, produto_nome, quantidade FROM pedido_itens "
            "WHERE pedido_id=? AND status='PRONTO'", (pedido_id,))
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cardapio")
@require_auth
def api_cardapio():
    try:
        from models.produto import Produto
        from models.estoque import Estoque
        produtos = Produto.listar()
        result = []
        for p in produtos:
            result.append({
                "id":             p["id"],
                "nome":           p["nome"],
                "codigo":         p.get("codigo", ""),
                "preco_venda":    float(p.get("preco_venda") or 0),
                "categoria_nome": p.get("categoria_nome") or "Sem categoria",
                "unidade":        p.get("unidade", "UN"),
                "estoque":        Estoque.saldo_total_produto(p["id"]),
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API pública ───────────────────────────────────────────────
def set_empresa_nome(nome: str):
    """Define o nome da empresa exibido no app garçom."""
    global _empresa_nome
    _empresa_nome = nome


def consumir_notificacoes() -> list[dict]:
    """Retorna e limpa a lista de novos pedidos (chamada pela thread de polling do PDV)."""
    with _lock:
        pendentes = list(_novos_pedidos)
        _novos_pedidos.clear()
    return pendentes


def iniciar(porta: int = 5000):
    """Sobe o Flask em thread daemon."""
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    t = threading.Thread(
        target=lambda: app.run(
            host="0.0.0.0", port=porta, debug=False, use_reloader=False),
        daemon=True,
    )
    t.start()
