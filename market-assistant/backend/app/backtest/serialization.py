import hashlib
import json
from typing import Any

import pandas as pd


def serialize_equity_curve(equity_curve: pd.Series) -> list[dict[str, Any]]:
    return [
        {"ts": ts.isoformat(), "value": float(value)}
        for ts, value in equity_curve.items()
    ]


def stats_hash(stats: dict[str, Any]) -> str:
    canonical = json.dumps(stats, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
