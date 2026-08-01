"""Experiment logging and reproducibility helpers (mandate §7.5)."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

EXPERIMENT_LOG = Path("logs/experiment_log.csv")
LOG_FIELDS = ["experiment_id", "timestamp_utc", "git_commit", "config_hash",
              "data_period", "pairs", "model_type", "parameters", "cost_scenario",
              "result_summary", "notes", "status"]


def config_hash(config: dict) -> str:
    """Stable short hash of a configuration dict."""
    blob = json.dumps(config, sort_keys=True, default=str).encode()
    return hashlib.sha256(blob).hexdigest()[:12]


def git_commit_or_empty() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=5,
                              check=True).stdout.strip()
    except Exception:
        return ""


def next_experiment_id(log_path: Path = EXPERIMENT_LOG) -> str:
    if not log_path.exists():
        return "EXP-001"
    with log_path.open() as f:
        rows = list(csv.DictReader(f))
    nums = [int(r["experiment_id"].split("-")[1]) for r in rows
            if r.get("experiment_id", "").startswith("EXP-")]
    return f"EXP-{(max(nums) + 1 if nums else 1):03d}"


def log_experiment(*, data_period: str, pairs: str, model_type: str,
                   parameters: dict, cost_scenario: str, result_summary: str,
                   notes: str = "", status: str = "pending_review",
                   log_path: Path = EXPERIMENT_LOG) -> str:
    """Append one experiment row; returns the experiment id."""
    exp_id = next_experiment_id(log_path)
    row = {
        "experiment_id": exp_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_commit_or_empty(),
        "config_hash": config_hash(parameters),
        "data_period": data_period, "pairs": pairs, "model_type": model_type,
        "parameters": json.dumps(parameters, sort_keys=True, default=str),
        "cost_scenario": cost_scenario, "result_summary": result_summary,
        "notes": notes, "status": status,
    }
    exists = log_path.exists()
    with log_path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)
    return exp_id
