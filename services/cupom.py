"""Servico de geracao de cupom nao fiscal em PDF."""
"""Estrutura pronta para NFC-e: cada secao mapeia para um campo XML."""
import datetime, os, textwrap
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
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

def gerar_cupom_pdf(venda: dict, itens: list, pagamentos: list,
                    empresa: dict, destino: str = None) -> str:
    """
    Gera cupom nao fiscal em PDF (80mm).
    Retorna o caminho do arquivo gerado.
    Estrutura preparada para substituicao por NFC-e XML.
    """
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab nao instalado. Execute: pip install reportlab")

    if not destino:
        base = Path.home() / "PDV_Cupons"
        base.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = str(base / "cupom_{}_{}.pdf".format(venda.get("numero","0"), ts))

    larg = LARGURA_MM * mm
    c = rl_canvas.Canvas(destino, pagesize=(larg, 800*mm))
    c.setFont(FONTE, TAMANHO)
    y = 790 * mm
    mg = MARGEM_MM * mm

    def linha(txt="", bold=False, tamanho=None):
        nonlocal y
        c.setFont(FONTE_B if bold else FONTE, tamanho or (TAMANHO_B if bold else TAMANHO))
        c.drawString(mg, y, txt[:56])
        y -= (tamanho or TAMANHO) * 1.6

    def separador(char="-"):
        linha(char * 48)

    def centralizado(txt, bold=False):
        nonlocal y
        c.setFont(FONTE_B if bold else FONTE, TAMANHO_B if bold else TAMANHO)
        tw = c.stringWidth(txt, FONTE_B if bold else FONTE, TAMANHO_B if bold else TAMANHO)
        c.drawString((larg - tw) / 2, y, txt)
        y -= (TAMANHO_B if bold else TAMANHO) * 1.6

    # CABECALHO
    centralizado(empresa.get("razao_social","EMPRESA"), bold=True)
    centralizado("CNPJ: " + empresa.get("cnpj",""))
    centralizado(empresa.get("endereco",""))
    if empresa.get("telefone"): centralizado("Tel: " + empresa["telefone"])
    separador("=")
    centralizado("CUPOM NAO FISCAL", bold=True)
    separador("=")
    linha("Venda #{}  {}".format(venda.get("numero",""), venda.get("criado_em","")[:16]))
    linha("Operador: " + str(venda.get("operador_nome","")))
    if venda.get("cliente_nome"): linha("Cliente: " + venda["cliente_nome"])
    separador()

    # ITENS
    linha("ITEM  DESCRICAO                  QTD   TOTAL", bold=True)
    separador()
    for i, it in enumerate(itens, 1):
        nome = str(it.get("produto_nome",""))[:22]
        qtd  = float(it.get("quantidade", 1))
        preco= float(it.get("preco_unitario", 0))
        sub  = float(it.get("subtotal", 0))
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
    if desconto > 0: linha("Desconto:             -R$ {:>8.2f}".format(desconto))
    linha("TOTAL:                 R$ {:>8.2f}".format(total), bold=True)
    separador()

    # PAGAMENTOS
    FORMAS = {"DINHEIRO":"Dinheiro","DEBITO":"Cartao Debito","CREDITO":"Cartao Credito","PIX":"Pix","VR":"Vale-Refeicao","VA":"Vale-Alimentacao","OUTROS":"Outros"}
    for pg in pagamentos:
        forma = FORMAS.get(pg.get("forma",""), pg.get("forma",""))
        parc  = int(pg.get("parcelas", 1))
        label = forma + (" {:.0f}x".format(parc) if parc > 1 else "")
        linha("{:<20s} R$ {:>8.2f}".format(label, float(pg.get("valor",0))))
    if troco > 0: linha("Troco:                 R$ {:>8.2f}".format(troco))
    separador("=")

    # RODAPE
    centralizado("Obrigado pela preferencia!")
    centralizado(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    centralizado("** NAO E DOCUMENTO FISCAL **")
    separador("=")
    y -= 10*mm

    # Recorta pagina no tamanho real usado
    altura_usada = 790*mm - y + 20*mm
    c.setPageSize((larg, altura_usada))
    c.save()
    return destino

def gerar_comanda_cozinha(pedido: dict, itens_novos: list, mesa: dict, destino: str = None) -> str:
    """Gera comanda de cozinha em PDF com itens nao impressos ainda."""
    if not HAS_REPORTLAB:
        raise RuntimeError("reportlab nao instalado.")
    if not destino:
        base = Path.home() / "PDV_Cupons"
        base.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = str(base / "comanda_{}_{}.pdf".format(pedido.get("numero",""), ts))
    larg = LARGURA_MM * mm
    c = rl_canvas.Canvas(destino, pagesize=(larg, 400*mm))
    y = 390*mm; mg = MARGEM_MM*mm
    def linha(txt="", bold=False):
        nonlocal y
        c.setFont(FONTE_B if bold else FONTE, TAMANHO_B if bold else TAMANHO)
        c.drawString(mg, y, txt[:56]); y -= TAMANHO_B*1.8
    linha("COMANDA DE COZINHA", bold=True)
    linha("-"*48)
    linha("Mesa {} | Pedido #{}".format(mesa.get("nome",""), pedido.get("numero","")))
    linha("Garcom: " + str(pedido.get("garcom_nome","")))
    linha(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    linha("-"*48)
    for it in itens_novos:
        linha("{:.0f}x  {}".format(float(it.get("quantidade",1)), it.get("produto_nome","")), bold=True)
        if it.get("obs"): linha("   OBS: " + str(it["obs"]))
    linha("-"*48)
    altura_usada = 390*mm - y + 10*mm
    c.setPageSize((larg, altura_usada)); c.save()
    return destino