"""Servico de geracao de cupom nao fiscal em PDF."""
import datetime, os
from pathlib import Path

try:
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

LARGURA_MM  = 80
MARGEM_MM   = 4
FONTE       = "Courier"
FONTE_B     = "Courier-Bold"
TAMANHO     = 7
TAMANHO_B   = 8


# ─────────────────────────────────────────────────────────────────────────────
# Canvas mock — apenas mede altura, não desenha
# ─────────────────────────────────────────────────────────────────────────────
class _MedidorCanvas:
    def setFont(self, *_): pass
    def drawString(self, *_): pass
    def stringWidth(self, txt, _, size):
        return len(txt) * size * 0.6  # aproximação suficiente para medir


# ─────────────────────────────────────────────────────────────────────────────
# Renderizadores
# ─────────────────────────────────────────────────────────────────────────────
def _renderizar_cupom(c, venda: dict, itens: list, pagamentos: list,
                      empresa: dict, larg: float, mg: float, y_ini: float) -> float:
    """Renderiza o cupom no canvas fornecido. Retorna y final."""
    y = y_ini

    def linha(txt="", bold=False, tamanho=None):
        nonlocal y
        sz = tamanho or (TAMANHO_B if bold else TAMANHO)
        c.setFont(FONTE_B if bold else FONTE, sz)
        c.drawString(mg, y, txt[:56])
        y -= sz * 1.6

    def separador(char="-"):
        linha(char * 48)

    def centralizado(txt, bold=False):
        nonlocal y
        font = FONTE_B if bold else FONTE
        sz   = TAMANHO_B if bold else TAMANHO
        c.setFont(font, sz)
        tw = c.stringWidth(txt, font, sz)
        c.drawString((larg - tw) / 2, y, txt)
        y -= sz * 1.6

    # CABEÇALHO
    centralizado(empresa.get("razao_social", empresa.get("nome", "EMPRESA")), bold=True)
    centralizado("CNPJ: " + empresa.get("cnpj", ""))
    _end = empresa.get("endereco", "")
    if _end:
        _num = empresa.get("numero", "")
        if _num: _end += ", " + _num
        _bairro = empresa.get("bairro", "")
        _cidade = empresa.get("cidade", "")
        _uf     = empresa.get("estado", "")
        if _bairro: _end += " - " + _bairro
        if _cidade: _end += ", " + _cidade + (" - " + _uf if _uf else "")
        centralizado(_end)
    if empresa.get("telefone"):
        centralizado("Tel: " + empresa["telefone"])
    separador("=")
    centralizado("CUPOM NAO FISCAL", bold=True)
    separador("=")
    linha("Venda #{}  {}".format(venda.get("numero", ""), venda.get("criado_em", "")[:16]))
    linha("Operador: " + str(venda.get("operador_nome", "")))
    if venda.get("cliente_nome"):
        linha("Cliente: " + venda["cliente_nome"])
    if venda.get("cliente_doc"):
        linha("CPF/CNPJ: " + venda["cliente_doc"])
    separador()

    # ITENS
    linha("ITEM  DESCRICAO                  QTD   TOTAL", bold=True)
    separador()
    for i, it in enumerate(itens, 1):
        nome  = str(it.get("produto_nome", ""))[:22]
        qtd   = float(it.get("quantidade", 1))
        preco = float(it.get("preco_unitario", 0))
        sub   = float(it.get("subtotal", 0))
        linha("{:02d}    {:<22s}".format(i, nome))
        linha("       {:>6.3f} x R$ {:>7.2f}  R$ {:>7.2f}".format(qtd, preco, sub))
        if it.get("desconto_valor") and float(it["desconto_valor"]) > 0:
            linha("       Desc: -R$ {:.2f}".format(float(it["desconto_valor"])))
    separador()

    # TOTAIS
    subtotal = float(venda.get("subtotal", 0))
    desconto = float(venda.get("desconto_valor", 0))
    total    = float(venda.get("total", 0))
    troco    = float(venda.get("troco", 0))
    linha("Subtotal:              R$ {:>8.2f}".format(subtotal))
    if desconto > 0:
        linha("Desconto:             -R$ {:>8.2f}".format(desconto))
    linha("TOTAL:                 R$ {:>8.2f}".format(total), bold=True)
    separador()

    # PAGAMENTOS
    FORMAS = {
        "DINHEIRO": "Dinheiro", "DEBITO": "Cartao Debito",
        "CREDITO": "Cartao Credito", "PIX": "Pix",
        "VR": "Vale-Refeicao", "VA": "Vale-Alimentacao", "OUTROS": "Outros",
    }
    for pg in pagamentos:
        forma = FORMAS.get(pg.get("forma", ""), pg.get("forma", ""))
        parc  = int(pg.get("parcelas", 1))
        label = forma + (" {:.0f}x".format(parc) if parc > 1 else "")
        linha("{:<20s} R$ {:>8.2f}".format(label, float(pg.get("valor", 0))))
    if troco > 0:
        linha("Troco:                 R$ {:>8.2f}".format(troco))
    separador("=")

    # RODAPÉ
    centralizado("Obrigado pela preferencia!")
    centralizado(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    centralizado("** NAO E DOCUMENTO FISCAL **")
    separador("=")

    return y


def _renderizar_comanda(c, pedido: dict, itens_novos: list, mesa: dict,
                        larg: float, mg: float, y_ini: float) -> float:
    """Renderiza a comanda no canvas fornecido. Retorna y final."""
    y = y_ini

    def linha(txt="", bold=False):
        nonlocal y
        c.setFont(FONTE_B if bold else FONTE, TAMANHO_B if bold else TAMANHO)
        c.drawString(mg, y, txt[:56])
        y -= TAMANHO_B * 1.8

    linha("COMANDA DE COZINHA", bold=True)
    linha("-" * 48)
    linha("Mesa {} | Pedido #{}".format(mesa.get("nome", ""), pedido.get("numero", "")))
    linha("Garcom: " + str(pedido.get("garcom_nome", "")))
    linha(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    linha("-" * 48)
    for it in itens_novos:
        linha("{:.0f}x  {}".format(float(it.get("quantidade", 1)), it.get("produto_nome", "")), bold=True)
        if it.get("obs"):
            linha("   OBS: " + str(it["obs"]))
    linha("-" * 48)
    return y


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────
def gerar_cupom_pdf(venda: dict, itens: list, pagamentos: list,
                    empresa: dict, destino: str = None) -> str:
    """
    Gera cupom nao fiscal em PDF (80mm).
    Retorna o caminho do arquivo gerado.

    Usa dois passos para determinar a altura exata da página antes de
    renderizar — evita PDFs em branco causados por redimensionamento
    após o desenho.
    """
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab nao instalado. Execute: pip install reportlab")

    if not destino:
        base = Path.home() / "PDV_Cupons"
        base.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = str(base / "cupom_{}_{}.pdf".format(venda.get("numero", "0"), ts))

    larg = LARGURA_MM * mm
    mg   = MARGEM_MM  * mm
    REF  = 100_000    # y de referência para a medição (valor arbitrário grande)

    # Passo 1: medir altura sem desenhar
    y_final  = _renderizar_cupom(_MedidorCanvas(), venda, itens, pagamentos,
                                 empresa, larg, mg, REF)
    altura   = (REF - y_final) + 2 * mg

    # Passo 2: desenhar no canvas com o tamanho correto
    c = rl_canvas.Canvas(destino, pagesize=(larg, altura))
    _renderizar_cupom(c, venda, itens, pagamentos, empresa, larg, mg, altura - mg)
    c.save()
    return destino


def _renderizar_conta_mesa(c, pedido: dict, itens: list, mesa: dict,
                           empresa: dict, larg: float, mg: float, y_ini: float) -> float:
    """Renderiza a conta da mesa (para apresentar ao cliente antes do pagamento)."""
    y = y_ini

    def linha(txt="", bold=False, tamanho=None):
        nonlocal y
        sz = tamanho or (TAMANHO_B if bold else TAMANHO)
        c.setFont(FONTE_B if bold else FONTE, sz)
        c.drawString(mg, y, txt[:56])
        y -= sz * 1.6

    def separador(char="-"):
        linha(char * 48)

    def centralizado(txt, bold=False):
        nonlocal y
        font = FONTE_B if bold else FONTE
        sz   = TAMANHO_B if bold else TAMANHO
        c.setFont(font, sz)
        tw = c.stringWidth(txt, font, sz)
        c.drawString((larg - tw) / 2, y, txt)
        y -= sz * 1.6

    # Cabeçalho empresa
    if empresa.get("razao_social") or empresa.get("nome"):
        centralizado(empresa.get("razao_social", empresa.get("nome", "")), bold=True)
    if empresa.get("cnpj"):
        centralizado("CNPJ: " + empresa["cnpj"])
    separador("=")
    centralizado("CONTA DA MESA", bold=True)
    separador("=")

    linha("Mesa: {}  |  Pedido #{}".format(mesa.get("nome", ""), pedido.get("numero", "")))
    linha("Garcom: " + str(pedido.get("garcom_nome", "")))
    linha(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    if pedido.get("pessoas", 1) > 1:
        linha("Pessoas: {}".format(pedido["pessoas"]))
    separador()

    # Itens
    linha("ITEM  DESCRICAO                  QTD   TOTAL", bold=True)
    separador()
    for i, it in enumerate(itens, 1):
        nome  = str(it.get("produto_nome", ""))[:22]
        qtd   = float(it.get("quantidade", 1))
        preco = float(it.get("preco_unitario", 0))
        sub   = float(it.get("subtotal", 0))
        linha("{:02d}    {:<22s}".format(i, nome))
        linha("       {:>6.3f} x R$ {:>7.2f}  R$ {:>7.2f}".format(qtd, preco, sub))
        if it.get("obs"):
            linha("       Obs: " + str(it["obs"]))
    separador()

    # Totais
    subtotal = float(pedido.get("subtotal", 0))
    desconto = float(pedido.get("desconto_valor", 0))
    total    = float(pedido.get("total", 0))
    if desconto > 0:
        linha("Subtotal:              R$ {:>8.2f}".format(subtotal))
        linha("Desconto:             -R$ {:>8.2f}".format(desconto))
    linha("TOTAL:                 R$ {:>8.2f}".format(total), bold=True)

    # Divisão por pessoa
    pessoas = int(pedido.get("pessoas", 1))
    if pessoas > 1 and total > 0:
        separador()
        por_pessoa = round(total / pessoas, 2)
        linha("Por pessoa ({} pessoas): R$ {:>6.2f}".format(pessoas, por_pessoa))

    separador("=")
    centralizado("Obrigado pela preferencia!")
    centralizado("** ESTE NAO E UM DOCUMENTO FISCAL **")
    separador("=")

    return y


def gerar_conta_mesa(pedido: dict, itens: list, mesa: dict,
                     empresa: dict = None, destino: str = None) -> str:
    """Gera a conta da mesa em PDF para apresentar ao cliente antes do pagamento."""
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab nao instalado.")

    if not destino:
        base = Path.home() / "PDV_Cupons"
        base.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = str(base / "conta_mesa_{}_{}.pdf".format(pedido.get("numero", ""), ts))

    empresa = empresa or {}
    larg = LARGURA_MM * mm
    mg   = MARGEM_MM  * mm
    REF  = 100_000

    # Passo 1: medir
    y_final = _renderizar_conta_mesa(_MedidorCanvas(), pedido, itens, mesa,
                                     empresa, larg, mg, REF)
    altura  = (REF - y_final) + 2 * mg

    # Passo 2: desenhar
    c = rl_canvas.Canvas(destino, pagesize=(larg, altura))
    _renderizar_conta_mesa(c, pedido, itens, mesa, empresa, larg, mg, altura - mg)
    c.save()
    return destino


def _renderizar_recibo_parcial(c, venda: dict, forma: str, valor_pago: float,
                               num_pessoa: int, total_pessoas: int,
                               empresa: dict, larg: float, mg: float, y_ini: float) -> float:
    """Renderiza comprovante de pagamento parcial por pessoa."""
    y = y_ini
    FORMAS = {
        "DINHEIRO": "Dinheiro", "DEBITO": "Cartao Debito",
        "CREDITO": "Cartao Credito", "PIX": "Pix",
        "VR": "Vale-Refeicao", "VA": "Vale-Alimentacao", "OUTROS": "Outros",
    }

    def linha(txt="", bold=False):
        nonlocal y
        sz = TAMANHO_B if bold else TAMANHO
        c.setFont(FONTE_B if bold else FONTE, sz)
        c.drawString(mg, y, txt[:56])
        y -= sz * 1.6

    def separador(char="-"):
        linha(char * 48)

    def centralizado(txt, bold=False):
        nonlocal y
        font = FONTE_B if bold else FONTE
        sz   = TAMANHO_B if bold else TAMANHO
        c.setFont(font, sz)
        tw = c.stringWidth(txt, font, sz)
        c.drawString((larg - tw) / 2, y, txt)
        y -= sz * 1.6

    centralizado(empresa.get("razao_social", empresa.get("nome", "EMPRESA")), bold=True)
    if empresa.get("cnpj"):
        centralizado("CNPJ: " + empresa["cnpj"])
    separador("=")
    centralizado("COMPROVANTE DE PAGAMENTO", bold=True)
    separador("=")

    linha("Venda #{}  {}".format(venda.get("numero", ""), (venda.get("criado_em") or "")[:16]))
    linha("Pessoa {} de {}".format(num_pessoa, total_pessoas), bold=True)
    if venda.get("operador_nome"):
        linha("Operador: " + str(venda["operador_nome"]))
    separador()

    total_venda  = float(venda.get("total", 0))
    total_pago   = float(venda.get("total_pago", 0))
    saldo_rest   = max(0.0, total_venda - total_pago)

    linha("Total da venda:  R$ {:>8.2f}".format(total_venda))
    separador()
    linha("Voce pagou:      R$ {:>8.2f}".format(valor_pago), bold=True)
    linha("Forma: {}".format(FORMAS.get(forma, forma)))
    if saldo_rest > 0.01:
        separador()
        linha("Saldo restante:  R$ {:>8.2f}".format(saldo_rest))
    separador("=")
    centralizado("Obrigado!")
    centralizado(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    centralizado("** NAO E DOCUMENTO FISCAL **")
    separador("=")
    return y


def gerar_recibo_parcial(venda: dict, forma: str, valor_pago: float,
                         num_pessoa: int, total_pessoas: int,
                         empresa: dict = None, destino: str = None) -> str:
    """Gera comprovante de pagamento parcial por pessoa em PDF."""
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab nao instalado.")

    if not destino:
        base = Path.home() / "PDV_Cupons"
        base.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = str(base / "recibo_{}_p{}_{}.pdf".format(
            venda.get("numero", "0"), num_pessoa, ts))

    empresa = empresa or {}
    larg = LARGURA_MM * mm
    mg   = MARGEM_MM  * mm
    REF  = 100_000

    y_final = _renderizar_recibo_parcial(_MedidorCanvas(), venda, forma, valor_pago,
                                         num_pessoa, total_pessoas, empresa, larg, mg, REF)
    altura  = (REF - y_final) + 2 * mg

    c = rl_canvas.Canvas(destino, pagesize=(larg, altura))
    _renderizar_recibo_parcial(c, venda, forma, valor_pago,
                               num_pessoa, total_pessoas, empresa, larg, mg, altura - mg)
    c.save()
    return destino


def gerar_comanda_cozinha(pedido: dict, itens_novos: list, mesa: dict,
                          destino: str = None) -> str:
    """Gera comanda de cozinha em PDF com itens nao impressos ainda."""
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab nao instalado.")

    if not destino:
        base = Path.home() / "PDV_Cupons"
        base.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = str(base / "comanda_{}_{}.pdf".format(pedido.get("numero", ""), ts))

    larg = LARGURA_MM * mm
    mg   = MARGEM_MM  * mm
    REF  = 100_000

    # Passo 1: medir
    y_final = _renderizar_comanda(_MedidorCanvas(), pedido, itens_novos, mesa,
                                  larg, mg, REF)
    altura  = (REF - y_final) + 2 * mg

    # Passo 2: desenhar
    c = rl_canvas.Canvas(destino, pagesize=(larg, altura))
    _renderizar_comanda(c, pedido, itens_novos, mesa, larg, mg, altura - mg)
    c.save()
    return destino
