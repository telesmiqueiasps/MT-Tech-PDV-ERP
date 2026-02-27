class Session:
    _usuario:    dict | None = None
    _empresa:    dict | None = None
    _permissoes: dict[str, bool] = {}

    @classmethod
    def iniciar(cls, usuario: dict, empresa: dict, permissoes: dict[str, bool]):
        cls._usuario    = dict(usuario)
        cls._empresa    = dict(empresa)
        cls._permissoes = permissoes

    @classmethod
    def encerrar(cls):
        cls._usuario    = None
        cls._empresa    = None
        cls._permissoes = {}

    @classmethod
    def ativa(cls) -> bool:
        return cls._usuario is not None

    @classmethod
    def usuario(cls) -> dict:
        if not cls._usuario:
            raise RuntimeError("Nenhuma sessão ativa.")
        return cls._usuario

    @classmethod
    def empresa(cls) -> dict:
        if not cls._empresa:
            raise RuntimeError("Nenhuma empresa na sessão.")
        return cls._empresa

    @classmethod
    def is_admin_global(cls) -> bool:
        return bool(cls._usuario.get("is_admin_global")) if cls._usuario else False

    @classmethod
    def usuario_id(cls) -> int | None:
        return cls._usuario.get("id") if cls._usuario else None

    @classmethod
    def nome(cls) -> str:
        if not cls._usuario:
            return ""
        return cls._usuario.get("nome") or cls._usuario.get("login", "")

    @classmethod
    def pode(cls, modulo: str, acao: str) -> bool:
        if cls.is_admin_global():
            return True
        return cls._permissoes.get(f"{modulo}:{acao}", False)