import os
import json
from typing import Any
from pydantic import BaseModel
from .model import AppConfig, ProviderFlags, ProviderKeys, ScannerSettings

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

def load_config(path: str = "config.yaml") -> AppConfig:
    if yaml is None:
        raise RuntimeError("PyYAML not installed. `pip install pyyaml`")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return AppConfig(**data)
