from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
import re

from .typesys import ANY, Type


class NativeFailure(Exception):
    def __init__(self, message: str, diagnostic_id: str | None = None) -> None:
        super().__init__(message)
        self.diagnostic_id = diagnostic_id


@dataclass(slots=True)
class Capabilities:
    allow_all: bool = False
    read_roots: tuple[Path, ...] = ()
    write_roots: tuple[Path, ...] = ()
    net_hosts: tuple[str, ...] = ()
    db_roots: tuple[Path, ...] = ()
    allow_ui: bool = False
    plugin_roots: tuple[Path, ...] = ()
    allow_process: bool = False
    env_names: tuple[str, ...] = ()
    allow_cloud: bool = False
    allow_device: bool = False

    @classmethod
    def safe(cls) -> "Capabilities":
        return cls()

    @staticmethod
    def _resolved(path: str | Path) -> Path:
        return Path(path).expanduser().resolve()

    @staticmethod
    def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
        for root in roots:
            try:
                path.relative_to(root.resolve())
                return True
            except ValueError:
                continue
        return False

    def require_read(self, path: str | Path) -> Path:
        target = self._resolved(path)
        if not self.allow_all and not self._inside(target, self.read_roots):
            raise NativeFailure(f"読み取り権限がありません: {target}。--allow-read を指定してください", "SAGA-R103")
        return target

    def require_write(self, path: str | Path) -> Path:
        target = self._resolved(path)
        if not self.allow_all and not self._inside(target, self.write_roots):
            raise NativeFailure(f"書き込み権限がありません: {target}。--allow-write を指定してください", "SAGA-R103")
        return target

    def require_db(self, path: str | Path) -> Path:
        target = self._resolved(path)
        if not self.allow_all and not self._inside(target, self.db_roots):
            raise NativeFailure(f"データベース利用権限がありません: {target}。--allow-db を指定してください", "SAGA-R103")
        return target

    @staticmethod
    def _split_endpoint(value: str) -> tuple[str, int | None]:
        text = value.strip()
        if not text:
            raise NativeFailure("空のネットワーク許可指定は使えません")
        if text.startswith("["):
            match = re.fullmatch(r"\[([^]]+)\](?::(\d+))?", text)
            if not match:
                raise NativeFailure(f"ネットワーク許可指定が正しくありません: {value}")
            return match.group(1).lower(), int(match.group(2)) if match.group(2) else None
        # A single ':' is host:port. Multiple ':' characters are an unbracketed IPv6 address.
        if text.count(":") == 1:
            name, possible_port = text.rsplit(":", 1)
            if possible_port.isdigit():
                return name.lower(), int(possible_port)
        return text.lower().strip("[]"), None

    @staticmethod
    def _host_matches(host: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        if pattern.startswith("*."):
            suffix = pattern[2:]
            return bool(suffix) and host.endswith("." + suffix) and host != suffix
        return host == pattern

    def require_net(self, host: str, port: int | None = None) -> None:
        normalized = host.lower().strip("[]").rstrip(".")
        if not normalized:
            raise NativeFailure("ネットワークホストが空です")
        if port is not None and not 0 <= port <= 65535:
            raise NativeFailure(f"ポート番号が範囲外です: {port}")
        if self.allow_all:
            return
        for entry in self.net_hosts:
            allowed_host, allowed_port = self._split_endpoint(entry)
            allowed_host = allowed_host.rstrip(".")
            if self._host_matches(normalized, allowed_host) and (allowed_port is None or allowed_port == port):
                return
        endpoint = f"[{normalized}]:{port}" if ":" in normalized and port is not None else (f"{normalized}:{port}" if port is not None else normalized)
        raise NativeFailure(f"ネットワーク権限がありません: {endpoint}。--allow-net {endpoint} を指定してください", "SAGA-R103")

    def require_env(self, name: str) -> None:
        if self.allow_all or name in self.env_names:
            return
        raise NativeFailure(f"環境変数の読み取り権限がありません: {name}。--allow-env {name} を指定してください", "SAGA-R103")

    def require_cloud(self) -> None:
        if not (self.allow_all or self.allow_cloud):
            raise NativeFailure("クラウドSDK権限がありません。--allow-cloud を指定してください", "SAGA-R103")

    def require_device(self) -> None:
        if not (self.allow_all or self.allow_device):
            raise NativeFailure("物理デバイス権限がありません。--allow-device を指定してください", "SAGA-R103")

    def require_process(self) -> None:
        if not (self.allow_all or self.allow_process):
            raise NativeFailure("外部プロセス起動権限がありません。--allow-process を指定してください", "SAGA-R103")

    def require_ui(self) -> None:
        if not (self.allow_all or self.allow_ui):
            raise NativeFailure("GUI権限がありません。--allow-ui を指定してください", "SAGA-R103")

    def require_plugin(self, path: str | Path) -> Path:
        target = self._resolved(path)
        if not self.allow_all and not self._inside(target, self.plugin_roots):
            raise NativeFailure(f"プラグイン読み込み権限がありません: {target}。--allow-plugin を指定してください", "SAGA-R103")
        return target


NativeImpl = Callable[["InterpreterLike", list[object]], object]


@dataclass(frozen=True, slots=True)
class NativeSignature:
    params: tuple[Type, ...] = ()
    returns: Type = ANY
    variadic: bool = False
    min_args: int | None = None


@dataclass(slots=True)
class NativeFunction:
    module: str
    name: str
    signature: NativeSignature
    impl: NativeImpl

    def __call__(self, interpreter: "InterpreterLike", args: list[object]) -> object:
        expected = len(self.signature.params)
        if self.signature.variadic:
            minimum = self.signature.min_args if self.signature.min_args is not None else expected
            if len(args) < minimum:
                raise NativeFailure(f"{self.module}.{self.name} の引数は最低 {minimum} 個必要です")
        elif len(args) != expected:
            raise NativeFailure(f"{self.module}.{self.name} の引数は {expected} 個必要です")
        validator = getattr(interpreter, "validate_native_value", None)
        if callable(validator):
            for index, (declared, value) in enumerate(zip(self.signature.params, args), start=1):
                validator(declared, value, f"{self.module}.{self.name} の第{index}引数")
        result = self.impl(interpreter, args)
        if callable(validator):
            validator(self.signature.returns, result, f"{self.module}.{self.name} の戻り値")
        return result

    def __repr__(self) -> str:
        return f"<native {self.module}.{self.name}>"


@dataclass(slots=True)
class NativeModule:
    name: str
    functions: dict[str, NativeFunction] = field(default_factory=dict)

    def get(self, name: str) -> NativeFunction:
        try:
            return self.functions[name]
        except KeyError as exc:
            raise NativeFailure(f"モジュール '{self.name}' に '{name}' はありません") from exc

    def __repr__(self) -> str:
        return f"<module {self.name}>"


class InterpreterLike:
    capabilities: Capabilities
    output: Callable[[str], None]

    def validate_native_value(self, expected: Type, value: object, label: str) -> None: ...
