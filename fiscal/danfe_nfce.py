"""Gerador de DANFE NFC-e em PDF — bobina térmica 80mm."""
import io
from pathlib import Path
from datetime import datetime


class DanfeNfce:
    LARGURA_MM = 80
    MARGEM_MM  = 4

    def gerar(self, doc_id: int, venda: dict, itens: list, pagamentos: list,
              config: dict, empresa: dict, protocolo: str,
              chave_acesso: str, qr_url: str) -> str:
        """Gera o PDF do DANFE e retorna o caminho do arquivo."""
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib.colors import red, black, white, HexColor

        # Diretório de saída
        danfe_dir = Path.home() / ".pdverp" / "danfe"
        danfe_dir.mkdir(parents=True, exist_ok=True)
        chave_safe = chave_acesso or str(doc_id)
        path = danfe_dir / f"{chave_safe}.pdf"

        w_mm = self.LARGURA_MM
        mg   = self.MARGEM_MM

        # Calcular altura dinamicamente
        n_itens  = len(itens)
        altura   = 120 + n_itens * 12 + 80  # estimativa em mm
        w   = w_mm * mm
        h   = altura * mm

        buf = io.BytesIO()
        c   = pdf_canvas.Canvas(buf, pagesize=(w, h))
        y   = h - mg * mm  # topo

        def line(txt: str, size: int = 7, bold: bool = False,
                 center: bool = False, color=black):
            nonlocal y
            face = "Helvetica-Bold" if bold else "Helvetica"
            c.setFont(face, size)
            c.setFillColor(color)
            if center:
                c.drawCentredString(w / 2, y, txt)
            else:
                c.drawString(mg * mm, y, txt)
            y -= (size + 2)

        def sep():
            nonlocal y
            c.setStrokeColor(HexColor("#CCCCCC"))
            c.line(mg * mm, y, (w_mm - mg) * mm, y)
            y -= 4

        # ── Homologação ──────────────────────────────────────────────
        if config.get("ambiente", 2) == 2:
            c.setFillColor(red)
            c.rect(0, y - 14, w, 16, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(w / 2, y - 10, "AMBIENTE DE HOMOLOGAÇÃO - SEM VALOR FISCAL")
            y -= 18

        # ── Cabeçalho ────────────────────────────────────────────────
        nome = empresa.get("razao_social") or empresa.get("nome", "EMPRESA")
        line(nome[:45], size=9, bold=True, center=True)
        cnpj = empresa.get("cnpj", "")
        line(f"CNPJ: {cnpj}", size=7, center=True)
        end  = f"{empresa.get('endereco','')} {empresa.get('numero','')}, {empresa.get('bairro','')}"
        line(end[:50], size=7, center=True)
        line(f"{empresa.get('cidade','')}/{empresa.get('estado','')}", size=7, center=True)
        sep()

        line("NFC-e — NOTA FISCAL DE CONSUMIDOR ELETRÔNICA", size=8, bold=True, center=True)
        sep()

        # ── Itens ────────────────────────────────────────────────────
        line("ITEM  DESCRIÇÃO              QTD   V.UNIT   TOTAL", size=6, bold=True)
        sep()
        for idx, item in enumerate(itens, 1):
            xprod = str(item.get("produto_nome", ""))[:22]
            qtd   = float(item.get("quantidade", 1))
            v_un  = float(item.get("preco_unitario", 0))
            total = float(item.get("subtotal", 0))
            line(f"{idx:2}  {xprod:<22} {qtd:5.2f} {v_un:7.2f} {total:7.2f}", size=6)
        sep()

        # ── Totais ───────────────────────────────────────────────────
        v_prod = sum(float(i.get("subtotal", 0)) for i in itens)
        v_desc = float(venda.get("desconto_valor", 0) or 0)
        v_nf   = float(venda.get("total", v_prod - v_desc))
        line(f"Subtotal:  R$ {v_prod:>10.2f}", size=7)
        if v_desc > 0:
            line(f"Desconto:  R$ {v_desc:>10.2f}", size=7)
        line(f"TOTAL:     R$ {v_nf:>10.2f}", size=9, bold=True)
        sep()

        # ── Pagamentos ───────────────────────────────────────────────
        line("FORMA DE PAGAMENTO", size=7, bold=True)
        for pag in pagamentos:
            forma = str(pag.get("forma", "DINHEIRO"))
            valor = float(pag.get("valor", 0))
            line(f"  {forma:<20} R$ {valor:>8.2f}", size=7)
        sep()

        # ── QR Code ─────────────────────────────────────────────────
        if qr_url:
            try:
                import qrcode
                qr = qrcode.QRCode(box_size=2, border=1)
                qr.add_data(qr_url)
                qr.make(fit=True)
                img_pil = qr.make_image(fill_color="black", back_color="white")
                img_buf = io.BytesIO()
                img_pil.save(img_buf, format="PNG")
                img_buf.seek(0)
                from reportlab.lib.utils import ImageReader
                img_rl = ImageReader(img_buf)
                qr_size = 30 * mm
                y -= qr_size + 2
                c.drawImage(img_rl, (w - qr_size) / 2, y, width=qr_size, height=qr_size)
                y -= 4
            except Exception:
                pass

        # ── Chave de acesso ──────────────────────────────────────────
        sep()
        line("CHAVE DE ACESSO", size=6, bold=True, center=True)
        ch = chave_acesso
        grupos = " ".join(ch[i:i+4] for i in range(0, len(ch), 4)) if ch else ""
        line(grupos[:55], size=5, center=True)

        # ── Protocolo ────────────────────────────────────────────────
        if protocolo:
            line(f"Protocolo: {protocolo}", size=6, center=True)
        line(f"Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", size=6, center=True)

        c.save()
        path.write_bytes(buf.getvalue())
        return str(path)
