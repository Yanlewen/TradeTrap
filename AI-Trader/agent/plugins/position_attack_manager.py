"""
Utility helpers for loading and normalising position-attack configuration.

The configuration can be toggled via environment variables:
- POSITION_ATTACK_ENABLED: when set to truthy value (1/true/on), attack is enabled.
  When set to falsy value (0/false/off), attack is disabled regardless of config.
- POSITION_ATTACK_CONFIG_PATH: optional path to JSON config overriding the default.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class PositionAttackSettings:
    enabled: bool
    interval_steps: int
    min_sell_ratio: float
    max_sell_ratio: float
    min_buy_ratio: float
    max_buy_ratio: float
    min_cash_reserve_ratio: float
    flag_field: str
    flag_value: str
    max_symbol_attempts: int
    min_injections_per_session: int
    max_injections_per_session: int
    buy_size_multiplier: float

    def normalised(self) -> "PositionAttackSettings":
        interval = self.interval_steps if self.interval_steps > 0 else 1
        sell_min = max(self.min_sell_ratio, 0.0)
        sell_max = max(self.max_sell_ratio, sell_min)
        buy_min = max(self.min_buy_ratio, 0.0)
        buy_max = max(self.max_buy_ratio, buy_min)
        reserve = min(max(self.min_cash_reserve_ratio, 0.0), 0.99)
        attempts = self.max_symbol_attempts if self.max_symbol_attempts > 0 else 3
        min_injections = max(self.min_injections_per_session, 1)
        max_injections = self.max_injections_per_session if self.max_injections_per_session > 0 else min_injections
        max_injections = max(max_injections, min_injections)
        buy_multiplier = self.buy_size_multiplier if self.buy_size_multiplier > 0 else 1.0

        return PositionAttackSettings(
            enabled=self.enabled,
            interval_steps=interval,
            min_sell_ratio=sell_min,
            max_sell_ratio=sell_max,
            min_buy_ratio=buy_min,
            max_buy_ratio=buy_max,
            min_cash_reserve_ratio=reserve,
            flag_field=self.flag_field or "attack_tag",
            flag_value=self.flag_value or "position_attack",
            max_symbol_attempts=attempts,
            min_injections_per_session=min_injections,
            max_injections_per_session=max_injections,
            buy_size_multiplier=buy_multiplier,
        )


class PositionAttackManager:
    DEFAULT_CONFIG = PositionAttackSettings(
        enabled=False,
        interval_steps=3,
        min_sell_ratio=0.2,
        max_sell_ratio=0.6,
        min_buy_ratio=0.4,
        max_buy_ratio=0.9,
        min_cash_reserve_ratio=0.05,
        flag_field="attack_tag",
        flag_value="position_attack",
        max_symbol_attempts=5,
        min_injections_per_session=1,
        max_injections_per_session=3,
        buy_size_multiplier=1.0,
    )

    def __init__(self, config_path: Optional[str | Path] = None) -> None:
        if config_path is None:
            default_path = Path(__file__).resolve().parents[2] / "prompts" / "position_attack_config.json"
            config_env = os.getenv("POSITION_ATTACK_CONFIG_PATH")
            config_path = config_env if config_env else str(default_path)
        self.config_path = Path(config_path)
        self._raw_config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception as exc:
            print(f"⚠️ Failed to load position attack config ({self.config_path}): {exc}")
        return {}

    def get_settings(self, signature: str) -> PositionAttackSettings:
        base = self._merge_dicts(
            self.DEFAULT_CONFIG.__dict__,
            {k: v for k, v in self._raw_config.items() if k != "per_signature"},
        )
        signature_overrides = {}
        per_signature = self._raw_config.get("per_signature")
        if isinstance(per_signature, dict):
            signature_overrides = per_signature.get(signature, {})

        merged = self._merge_dicts(base, signature_overrides)

        enabled_value = merged.get("enabled", False)
        if isinstance(enabled_value, str):
            enabled_value = enabled_value.strip().lower() in {"1", "true", "yes", "on"}
        else:
            enabled_value = bool(enabled_value)

        settings = PositionAttackSettings(
            enabled=enabled_value,
            interval_steps=int(merged.get("interval_steps", 3)),
            min_sell_ratio=float(merged.get("min_sell_ratio", 0.2)),
            max_sell_ratio=float(merged.get("max_sell_ratio", 0.6)),
            min_buy_ratio=float(merged.get("min_buy_ratio", 0.4)),
            max_buy_ratio=float(merged.get("max_buy_ratio", 0.9)),
            min_cash_reserve_ratio=float(merged.get("min_cash_reserve_ratio", 0.05)),
            flag_field=str(merged.get("flag_field", "attack_tag")),
            flag_value=str(merged.get("flag_value", "position_attack")),
            max_symbol_attempts=int(merged.get("max_symbol_attempts", 5)),
            min_injections_per_session=int(merged.get("min_injections_per_session", 1)),
            max_injections_per_session=int(merged.get("max_injections_per_session", 3)),
            buy_size_multiplier=float(merged.get("buy_size_multiplier", 1.0)),
        )
        return settings.normalised()

    @staticmethod
    def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if value is None:
                continue
            merged[key] = value
        return merged

