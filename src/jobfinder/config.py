from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


class _StrictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _CompanyConfig(_StrictConfig):
    name: str
    token: str


class _AtsConfig(_StrictConfig):
    name: str
    endpoint: str
    companies: list[_CompanyConfig]


class _SearchConfig(_StrictConfig):
    locations: list[str] = Field(min_length=1)


class _RetryConfig(_StrictConfig):
    number: int = Field(ge=0)
    backoff_factor: float = Field(ge=0)
    respect_retry_after_header: bool
    status_forcelist: list[int]


class _HttpConfig(_StrictConfig):
    timeout_s: float = Field(gt=0)
    delay_s: float = Field(ge=0)
    retry: _RetryConfig


class _JsonStorageConfig(_StrictConfig):
    storage_type: Literal["json"] = Field(alias="type")
    data_dir: Path


_StorageConfig = _JsonStorageConfig


class Config(_StrictConfig):
    ats: list[_AtsConfig]
    http: _HttpConfig
    search: _SearchConfig
    storage: _StorageConfig


def load_config(path: Path) -> Config:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Config.model_validate(data)
