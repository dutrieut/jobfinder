from collections.abc import Callable

from ..config import _StorageConfig
from .json_store import JsonStore
from .store import JobStore


def _build_json(config: _StorageConfig) -> JobStore:
    return JsonStore(root=config.data_dir)


_BUILDERS: dict[str, Callable[[_StorageConfig], JobStore]] = {
    "json": _build_json,
}


def build_store(config: _StorageConfig) -> JobStore:
    try:
        builder = _BUILDERS[config.storage_type]
    except KeyError:
        supported = ", ".join(sorted(_BUILDERS))
        raise ValueError(
            f"Unsupported storage type {config.storage_type!r} (supported: {supported})"
        ) from None
    return builder(config)
