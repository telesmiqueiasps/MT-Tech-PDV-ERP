"""
Updater — verifica e aplica atualizações automáticas do executável.

Fluxo:
  verificar()         → GET /versao-atual, retorna dict ou None (silencioso)
  baixar_e_aplicar()  → baixa PDV_novo.exe, cria .bat e reinicia
"""

import json
import subprocess
import sys
import urllib.request
from pathlib import Path


class Updater:
    # ── Caminhos ──────────────────────────────────────────────────

    def _raiz(self) -> Path:
        """Raiz do projeto (dev) ou pasta do .exe (PyInstaller)."""
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).parent.parent

    def versao_atual(self) -> str:
        try:
            return (self._raiz() / "versao.txt").read_text(encoding="utf-8").strip()
        except Exception:
            return "0.0.0"

    # ── Comparação semântica ──────────────────────────────────────

    def _maior(self, nova: str, atual: str) -> bool:
        try:
            def parse(v: str) -> tuple:
                return tuple(int(x) for x in v.strip().split("."))
            return parse(nova) > parse(atual)
        except Exception:
            return False

    # ── Verificação online ────────────────────────────────────────

    def verificar(self) -> dict | None:
        """
        Consulta o servidor. Retorna dict {versao, url_download, obrigatoria,
        novidades} se houver versão nova, ou None se atualizado / sem internet.
        Nunca lança exceção.
        """
        try:
            from models.licenca import _SERVIDOR_URL
            url = f"{_SERVIDOR_URL}/versao-atual"
            req = urllib.request.Request(
                url, headers={"User-Agent": f"PDV-ERP/{self.versao_atual()}"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data: dict = json.loads(resp.read().decode("utf-8"))

            if self._maior(data.get("versao", "0.0.0"), self.versao_atual()):
                return data
            return None
        except Exception:
            return None

    # ── Download e aplicação ──────────────────────────────────────

    def baixar_e_aplicar(self, url: str, callback_progresso=None) -> None:
        """
        1. Baixa o novo .exe como PDV_novo.exe na pasta do executável atual.
        2. Cria _atualizar_pdv.bat que substitui o .exe e reinicia.
        3. Executa o .bat e encerra o processo com sys.exit(0).

        callback_progresso(int) é chamado com 0-100 durante o download.
        Funciona tanto em desenvolvimento quanto como .exe PyInstaller.
        """
        exe_atual = Path(sys.executable)
        exe_novo  = exe_atual.parent / "PDV_novo.exe"

        # ── Download ─────────────────────────────────────────────
        req = urllib.request.Request(
            url, headers={"User-Agent": f"PDV-ERP/{self.versao_atual()}"}
        )
        with urllib.request.urlopen(req) as resp:
            total   = int(resp.headers.get("Content-Length") or 0)
            baixado = 0
            with open(exe_novo, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    baixado += len(chunk)
                    if callback_progresso and total:
                        callback_progresso(min(99, baixado * 100 // total))

        if callback_progresso:
            callback_progresso(100)

        # ── Script de substituição ────────────────────────────────
        bat_path = exe_atual.parent / "_atualizar_pdv.bat"
        bat = (
            "@echo off\r\n"
            "timeout /t 2 /nobreak >nul\r\n"
            f'move /y "{exe_novo}" "{exe_atual}"\r\n'
            f'start "" "{exe_atual}"\r\n'
            'del "%~f0"\r\n'
        )
        bat_path.write_text(bat, encoding="cp1252")

        subprocess.Popen(
            [str(bat_path)],
            shell=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        sys.exit(0)
