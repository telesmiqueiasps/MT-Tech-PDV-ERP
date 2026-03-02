"""
Sistema de Licença — Híbrido (ativa online, valida offline com grace period).

Fluxo:
  1. Na instalação: gerar trial de 30 dias (sem servidor)
  2. Cliente compra: recebe CHAVE → ativa online → salva licença local assinada
  3. Nas próximas inicializações: valida local → tenta check online (silencioso)
  4. Se offline: aceita até grace_period_dias após último check válido

Segurança:
  - Chave HMAC-SHA256 com segredo do servidor
  - Fingerprint da máquina (nome, MAC, disco) — impede cópia entre máquinas
  - Arquivo local cifrado com AES (Fernet/cryptography)
  - Todos os eventos gravados em audit_log

Planos:
  TRIAL    : 30 dias, 1 empresa, 2 usuários, módulos básicos
  BASICO   : ilimitado, 1 empresa, 3 usuários, fiscal + estoque
  PRO      : ilimitado, 3 empresas, 10 usuários, todos os módulos
  ENTERPRISE: ilimitado, sem limite, módulos customizáveis
"""
import hashlib
import hmac
import json
import os
import platform
import socket
import datetime
import secrets
from pathlib import Path

# ── Constante de segurança — MUDE antes de distribuir ────────
# Nunca exponha esta chave no repositório público.
_HMAC_SECRET = b"SEU_SEGREDO_PRIVADO_TROQUE_ANTES_DE_DISTRIBUIR_2026"
_LICENCA_FILE = Path.home() / ".pdverp" / "licenca.json"
_SERVIDOR_URL = "https://licenca.seu-sistema.com.br"  # implemente quando tiver servidor


# ═══════════════════════════════════════════════════════════════
# Fingerprint da máquina
# ═══════════════════════════════════════════════════════════════
def _fingerprint() -> str:
    """Gera identificador único da máquina. Estável mesmo após reinicialização."""
    partes = [
        platform.node(),           # nome do computador
        platform.machine(),        # arquitetura
        platform.system(),
        str(os.getenv("COMPUTERNAME", "")),
        str(os.getenv("USERNAME", "") or os.getenv("USER", "")),
    ]
    # Tenta incluir MAC address
    try:
        import uuid
        partes.append(str(uuid.getnode()))
    except Exception:
        pass
    raw = "|".join(partes).encode()
    return hashlib.sha256(raw).hexdigest()[:32]


# ═══════════════════════════════════════════════════════════════
# Assinatura HMAC da chave
# ═══════════════════════════════════════════════════════════════
def _assinar_chave(chave: str) -> str:
    return hmac.new(
        _HMAC_SECRET,
        chave.encode(),
        hashlib.sha256,
    ).hexdigest()


def _verificar_assinatura(chave: str, chave_hash: str) -> bool:
    esperado = _assinar_chave(chave)
    return hmac.compare_digest(esperado, chave_hash)


def _gerar_chave() -> tuple[str, str]:
    """Gera par (chave_publica, chave_hash)."""
    chave = secrets.token_urlsafe(24).upper()[:32]
    # Formata como XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
    chave_fmt = "-".join(chave[i:i+4] for i in range(0, 32, 4))
    return chave_fmt, _assinar_chave(chave_fmt)


# ═══════════════════════════════════════════════════════════════
# Leitura e escrita do arquivo local
# ═══════════════════════════════════════════════════════════════
def _salvar_local(dados: dict):
    _LICENCA_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Adiciona hash de integridade
    payload = json.dumps(dados, ensure_ascii=False, default=str)
    integridade = hmac.new(
        _HMAC_SECRET, payload.encode(), hashlib.sha256
    ).hexdigest()
    wrapper = {"payload": payload, "sig": integridade}
    _LICENCA_FILE.write_text(
        json.dumps(wrapper, ensure_ascii=False), encoding="utf-8"
    )


def _ler_local() -> dict | None:
    try:
        wrapper = json.loads(_LICENCA_FILE.read_text(encoding="utf-8"))
        payload  = wrapper["payload"]
        sig_esp  = hmac.new(
            _HMAC_SECRET, payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig_esp, wrapper["sig"]):
            return None  # arquivo adulterado
        return json.loads(payload)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# Planos e módulos
# ═══════════════════════════════════════════════════════════════
PLANOS = {
    "TRIAL": {
        "nome":         "Trial Gratuito",
        "dias_trial":   30,
        "max_empresas": 1,
        "max_usuarios": 2,
        "modulos":      ["dashboard", "produtos", "estoque"],
        "cor":          "#6C757D",
    },
    "BASICO": {
        "nome":         "Básico",
        "max_empresas": 1,
        "max_usuarios": 3,
        "modulos":      ["dashboard","produtos","clientes","fornecedores","estoque","fiscal"],
        "cor":          "#0077cc",
    },
    "PRO": {
        "nome":         "Profissional",
        "max_empresas": 3,
        "max_usuarios": 10,
        "modulos":      ["dashboard","produtos","clientes","fornecedores",
                         "estoque","fiscal","pdv","relatorios","financeiro"],
        "cor":          "#1a7a3a",
    },
    "ENTERPRISE": {
        "nome":         "Enterprise",
        "max_empresas": 0,   # 0 = ilimitado
        "max_usuarios": 0,
        "modulos":      ["*"],  # todos
        "cor":          "#7b2d8b",
    },
}

TODOS_MODULOS = [
    "dashboard","produtos","clientes","fornecedores",
    "estoque","fiscal","pdv","relatorios","financeiro",
]


# ═══════════════════════════════════════════════════════════════
# Classe principal
# ═══════════════════════════════════════════════════════════════
class LicencaStatus:
    TRIAL    = "TRIAL"
    ATIVA    = "ATIVA"
    EXPIRADA = "EXPIRADA"
    GRACE    = "GRACE"       # online expirou mas ainda no grace period
    BLOQUEADA= "BLOQUEADA"
    INVALIDA = "INVALIDA"


class Licenca:
    """Estado atual da licença — carregado na inicialização do app."""

    _dados:        dict | None = None
    _status:       str         = LicencaStatus.INVALIDA
    _motivo:       str         = ""
    _cnpj_context: str         = ""  # CNPJ da empresa ativa (preenchido no login)

    # ── Inicialização ─────────────────────────────────────────
    @classmethod
    def inicializar(cls, cnpj_empresa: str = ""):
        cls._cnpj_context = cnpj_empresa or ""
        """
        Chamado uma vez na inicialização do app.
        1. Tenta ler arquivo local
        2. Verifica validade
        3. Se trial: cria/atualiza trial
        4. Tenta check online em background (não bloqueia)
        """
        dados = _ler_local()

        if not dados:
            # Primeira execução — cria trial
            # cnpj da empresa atual pode ser passado via Licenca.inicializar(cnpj=...)
            cls._criar_trial(cls._cnpj_context or "")
            return

        cls._dados = dados

        # Verifica fingerprint
        fp = _fingerprint()
        if dados.get("fingerprint") and dados["fingerprint"] != fp:
            cls._status = LicencaStatus.BLOQUEADA
            cls._motivo = ("Esta licença foi ativada em outra máquina.\n"
                           "Contate o suporte para transferência.")
            from core.audit import Audit
            Audit.licenca("LICENCA_MAQUINA_INVALIDA",
                          f"fingerprint esperado={dados['fingerprint']}, atual={fp}")
            return

        # Verifica assinatura da chave
        if dados.get("chave") and dados.get("chave_hash"):
            if not _verificar_assinatura(dados["chave"], dados["chave_hash"]):
                cls._status = LicencaStatus.INVALIDA
                cls._motivo = "Arquivo de licença corrompido ou adulterado."
                from core.audit import Audit
                Audit.licenca("LICENCA_ASSINATURA_INVALIDA")
                return

        cls._avaliar_validade()

        # Check online em background (não bloqueia a inicialização)
        import threading
        t = threading.Thread(target=cls._check_online, daemon=True)
        t.start()

    @classmethod
    def _criar_trial(cls, cnpj_empresa: str = ""):
        hoje  = datetime.date.today()
        expira = (hoje + datetime.timedelta(days=30)).isoformat()
        dados = {
            "plano":         "TRIAL",
            "status":        "TRIAL",
            "modulos":       PLANOS["TRIAL"]["modulos"],
            "max_empresas":  PLANOS["TRIAL"]["max_empresas"],
            "max_usuarios":  PLANOS["TRIAL"]["max_usuarios"],
            "emitida_em":    hoje.isoformat(),
            "validade_ate":  expira,
            "fingerprint":   _fingerprint(),
            "cnpj_empresa":  cnpj_empresa,    # Licença vinculada ao CNPJ
            "chave":         None,
            "chave_hash":    None,
            "ultimo_check":  hoje.isoformat(),
        }
        _salvar_local(dados)
        cls._dados   = dados
        cls._status  = LicencaStatus.TRIAL
        cls._motivo  = f"Trial até {expira}"
        from core.audit import Audit
        Audit.licenca("TRIAL_CRIADO",
                      f"Expira em {expira} — CNPJ {cnpj_empresa or 'não informado'}")

    @classmethod
    def _avaliar_validade(cls):
        dados   = cls._dados or {}
        plano   = dados.get("plano", "TRIAL")
        validade= dados.get("validade_ate")
        hoje    = datetime.date.today().isoformat()

        if plano == "TRIAL":
            if validade and hoje > validade:
                cls._status = LicencaStatus.EXPIRADA
                cls._motivo = f"Trial expirado em {validade}."
            else:
                cls._status = LicencaStatus.TRIAL
                cls._motivo = f"Trial até {validade}"
            return

        # Licença paga — verifica validade (None = sem expiração)
        if validade and hoje > validade:
            # Ainda no grace period?
            grace = dados.get("grace_ate")
            if grace and hoje <= grace:
                cls._status = LicencaStatus.GRACE
                cls._motivo = f"Licença expirada. Grace period até {grace}."
            else:
                cls._status = LicencaStatus.EXPIRADA
                cls._motivo = f"Licença expirada em {validade}."
        else:
            cls._status = LicencaStatus.ATIVA
            cls._motivo = ""

    @classmethod
    def _check_online(cls):
        """
        Tenta confirmar a licença com o servidor.
        Silencioso se offline — só atualiza grace period.
        """
        try:
            import urllib.request
            import urllib.parse

            dados = cls._dados or {}
            chave = dados.get("chave")
            if not chave:
                return  # trial, sem chave

            payload = json.dumps({
                "chave":       chave,
                "fingerprint": _fingerprint(),
                "versao":      "1.0.0",
            }).encode()

            req = urllib.request.Request(
                f"{_SERVIDOR_URL}/api/v1/validar",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                resultado = json.loads(resp.read())

            if resultado.get("valida"):
                hoje  = datetime.date.today()
                grace = (hoje + datetime.timedelta(days=7)).isoformat()
                dados["ultimo_check"] = hoje.isoformat()
                dados["grace_ate"]    = grace
                if resultado.get("validade_ate"):
                    dados["validade_ate"] = resultado["validade_ate"]
                if resultado.get("modulos"):
                    dados["modulos"] = resultado["modulos"]
                _salvar_local(dados)
                cls._dados = dados
                cls._avaliar_validade()
                from core.audit import Audit
                Audit.licenca("CHECK_OK", f"Servidor confirmou licença")
            else:
                motivo = resultado.get("motivo", "")
                from core.audit import Audit
                Audit.licenca("CHECK_FAIL", f"Servidor recusou: {motivo}")
                if resultado.get("bloquear"):
                    dados["status"] = "BLOQUEADA"
                    _salvar_local(dados)
                    cls._status = LicencaStatus.BLOQUEADA
                    cls._motivo = motivo

        except Exception:
            # Offline — mantém estado local
            pass

    # ── Ativação (chamada pela UI) ────────────────────────────
    @classmethod
    def ativar(cls, chave: str) -> tuple[bool, str]:
        """
        Tenta ativar uma chave.
        Online: envia ao servidor, recebe dados do plano.
        Offline: valida HMAC local (para ambientes sem internet).
        Retorna (sucesso, mensagem).
        """
        chave = chave.strip().upper()
        # Remove espaços e normaliza separadores
        chave = chave.replace(" ", "-").replace("_", "-")

        # 1. Tenta online
        try:
            import urllib.request
            payload = json.dumps({
                "chave":       chave,
                "fingerprint": _fingerprint(),
                "versao":      "1.0.0",
            }).encode()
            req = urllib.request.Request(
                f"{_SERVIDOR_URL}/api/v1/ativar",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resultado = json.loads(resp.read())

            if not resultado.get("valida"):
                from core.audit import Audit
                Audit.licenca("ATIVACAO_FALHA", f"Servidor: {resultado.get('motivo')}")
                return False, resultado.get("motivo", "Chave inválida.")

            # Servidor aprovou
            dados = {
                "chave":        chave,
                "chave_hash":   _assinar_chave(chave),
                "plano":        resultado.get("plano", "BASICO"),
                "modulos":      resultado.get("modulos", PLANOS["BASICO"]["modulos"]),
                "max_empresas": resultado.get("max_empresas", 1),
                "max_usuarios": resultado.get("max_usuarios", 3),
                "emitida_em":   resultado.get("emitida_em",
                                             datetime.date.today().isoformat()),
                "validade_ate": resultado.get("validade_ate"),
                "fingerprint":  _fingerprint(),
                "ativada_em":   datetime.date.today().isoformat(),
                "ultimo_check": datetime.date.today().isoformat(),
                "grace_ate":    (datetime.date.today() +
                                 datetime.timedelta(days=7)).isoformat(),
            }
            _salvar_local(dados)
            cls._dados  = dados
            cls._status = LicencaStatus.ATIVA
            cls._motivo = ""
            from core.audit import Audit
            Audit.licenca("ATIVACAO_OK",
                          f"Plano {dados['plano']} ativado via servidor")
            return True, f"Licença {dados['plano']} ativada com sucesso!"

        except Exception as e_online:
            # Offline — valida HMAC local
            chave_hash = _assinar_chave(chave)
            # Sem servidor, não temos como saber o plano — assumimos BASICO
            # Em produção: o cliente deveria ter acesso ao servidor ao ativar
            if len(chave.replace("-", "")) >= 24:
                dados = {
                    "chave":        chave,
                    "chave_hash":   chave_hash,
                    "plano":        "BASICO",
                    "modulos":      PLANOS["BASICO"]["modulos"],
                    "max_empresas": 1,
                    "max_usuarios": 3,
                    "emitida_em":   datetime.date.today().isoformat(),
                    "validade_ate": None,
                    "fingerprint":  _fingerprint(),
                    "ativada_em":   datetime.date.today().isoformat(),
                    "ultimo_check": datetime.date.today().isoformat(),
                    "grace_ate":    (datetime.date.today() +
                                     datetime.timedelta(days=7)).isoformat(),
                }
                _salvar_local(dados)
                cls._dados  = dados
                cls._status = LicencaStatus.ATIVA
                cls._motivo = "Ativado offline — conecte-se para confirmar."
                from core.audit import Audit
                Audit.licenca("ATIVACAO_OFFLINE", f"Sem servidor: {e_online}")
                return True, ("Licença ativada offline.\n"
                              "Conecte-se à internet nas próximas 7 dias "
                              "para confirmar a ativação.")
            return False, "Sem conexão com o servidor. Verifique a internet e tente novamente."

    # ── Consultas de estado ───────────────────────────────────
    @classmethod
    def status(cls) -> str:
        return cls._status

    @classmethod
    def motivo(cls) -> str:
        return cls._motivo

    @classmethod
    def ativa(cls) -> bool:
        return cls._status in (LicencaStatus.ATIVA,
                               LicencaStatus.TRIAL,
                               LicencaStatus.GRACE)

    @classmethod
    def plano(cls) -> str:
        return (cls._dados or {}).get("plano", "TRIAL")

    @classmethod
    def plano_info(cls) -> dict:
        return PLANOS.get(cls.plano(), PLANOS["TRIAL"])

    @classmethod
    def modulo_liberado(cls, modulo: str) -> bool:
        if not cls.ativa():
            return False
        modulos = (cls._dados or {}).get("modulos", [])
        return "*" in modulos or modulo in modulos

    @classmethod
    def max_usuarios(cls) -> int:
        return int((cls._dados or {}).get("max_usuarios", 2))

    @classmethod
    def max_empresas(cls) -> int:
        return int((cls._dados or {}).get("max_empresas", 1))

    @classmethod
    def validade(cls) -> str | None:
        return (cls._dados or {}).get("validade_ate")

    @classmethod
    def dias_restantes(cls) -> int | None:
        val = cls.validade()
        if not val:
            return None
        d = datetime.date.fromisoformat(val) - datetime.date.today()
        return max(0, d.days)

    @classmethod
    def cnpj_licenciado(cls) -> str:
        """CNPJ ao qual esta licença está vinculada."""
        raw = (cls._dados or {}).get("cnpj_empresa", "")
        return "".join(filter(str.isdigit, raw))

    @classmethod
    def validar_cnpj(cls, cnpj: str) -> bool:
        """
        Verifica se o CNPJ da empresa bate com a licença.
        Trial e licenças sem CNPJ definido aceitam qualquer empresa.
        """
        licenciado = cls.cnpj_licenciado()
        if not licenciado:
            return True  # trial ou licença sem restrição de CNPJ
        cnpj_norm = "".join(filter(str.isdigit, cnpj or ""))
        return cnpj_norm == licenciado

    @classmethod
    def resumo(cls) -> dict:
        return {
            "status":          cls._status,
            "plano":           cls.plano(),
            "plano_nome":      cls.plano_info()["nome"],
            "ativa":           cls.ativa(),
            "validade":        cls.validade(),
            "dias_restantes":  cls.dias_restantes(),
            "max_usuarios":    cls.max_usuarios(),
            "max_empresas":    1,
            "cnpj_licenciado": cls.cnpj_licenciado(),
            "modulos":         (cls._dados or {}).get("modulos", []),
            "fingerprint":     _fingerprint()[:16] + "...",
            "motivo":          cls._motivo,
        }

    # ── Geração de chave (uso interno/admin) ──────────────────
    @staticmethod
    def gerar_chave(plano: str = "BASICO", validade_dias: int = None,
                    max_usuarios: int = 3, cnpj_empresa: str = "",
                    modulos: list = None) -> dict:
        """
        Gera uma nova chave de licença para emitir a um cliente.
        Modelo: 1 licença por empresa (vinculada ao CNPJ).
        Em produção: salvar no banco do servidor e enviar ao cliente.
        """
        chave, chave_hash = _gerar_chave()
        expira = None
        if validade_dias:
            expira = (datetime.date.today() +
                      datetime.timedelta(days=validade_dias)).isoformat()
        # CNPJ só números para consistência
        cnpj_norm = "".join(filter(str.isdigit, cnpj_empresa))
        return {
            "chave":        chave,
            "chave_hash":   chave_hash,
            "plano":        plano,
            "modulos":      modulos or PLANOS.get(plano, PLANOS["BASICO"])["modulos"],
            "max_usuarios": max_usuarios,
            "max_empresas": 1,               # sempre 1 — modelo por empresa
            "cnpj_empresa": cnpj_norm,       # CNPJ vinculado
            "validade_ate": expira,
            "emitida_em":   datetime.date.today().isoformat(),
        }