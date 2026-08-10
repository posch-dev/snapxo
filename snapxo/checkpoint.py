# Records how far a run got, so an interrupted one can pick up where it stopped.
# Written during the run, deleted once everything is through.

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path

CHECKPOINT_FILE = ".snaporganizer_checkpoint.json"
CHECKPOINT_VERSION = 2

_VOLATILE_KEYS = {"resume", "verbose", "yes", "info"}  # don't change what a run produces
_FLUSH_EVERY = 25                                      # files between saves


def config_fingerprint(config) -> str:
    # A checkpoint from a different export, output folder or set of filters must not be reused.
    data = asdict(config) if is_dataclass(config) else dict(config)
    reduced = {k: str(v) for k, v in sorted(data.items()) if k not in _VOLATILE_KEYS}
    blob = json.dumps(reduced, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


class Checkpoint:
    def __init__(self, output_dir: Path, fingerprint: str = "", enabled: bool = True):
        self.path = output_dir / CHECKPOINT_FILE
        self.fingerprint = fingerprint
        self.enabled = enabled
        self._pending = 0
        self.data: dict = self._empty()

    def _empty(self) -> dict:
        return {
            "version": CHECKPOINT_VERSION,
            "fingerprint": self.fingerprint,
            "completed_steps": [],
            "processed_files": {},
            "dup_alias": {},
        }

    def load(self) -> bool:
        # A stale or unreadable checkpoint is discarded, never half-applied.
        if not self.path.is_file():
            return False
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            return False

        if data.get("version") != CHECKPOINT_VERSION:
            return False
        if data.get("fingerprint") != self.fingerprint:
            return False

        self.data = {
            "version": CHECKPOINT_VERSION,
            "fingerprint": self.fingerprint,
            "completed_steps": list(data.get("completed_steps") or []),
            "processed_files": {
                step: set(names) for step, names in (data.get("processed_files") or {}).items()
            },
            "dup_alias": dict(data.get("dup_alias") or {}),
        }
        return bool(self.data["completed_steps"] or self.data["processed_files"])

    def summary(self) -> str:
        steps = len(self.data["completed_steps"])
        files = sum(len(v) for v in self.data["processed_files"].values())
        return f"{steps} steps, {files} files already done"

    def is_step_done(self, step: str) -> bool:
        return step in self.data["completed_steps"]

    def complete_step(self, step: str):
        if step not in self.data["completed_steps"]:
            self.data["completed_steps"].append(step)
        self.flush()

    def is_file_done(self, step: str, name: str) -> bool:
        return name in self.data["processed_files"].get(step, ())

    def mark_file_done(self, step: str, name: str):
        self.data["processed_files"].setdefault(step, set()).add(name)
        self._pending += 1
        if self._pending >= _FLUSH_EVERY:
            self.flush()

    # Dedup deletes files, so re-running it finds nothing and loses the aliases.
    @property
    def dup_alias(self) -> dict[str, str]:
        return self.data["dup_alias"]

    def store_dup_alias(self, alias: dict[str, str]):
        self.data["dup_alias"] = dict(alias)
        self.flush()

    def flush(self):
        self._pending = 0
        if not self.enabled:
            return
        payload = dict(self.data)
        payload["processed_files"] = {
            step: sorted(names) for step, names in self.data["processed_files"].items()
        }
        # Written to a sibling first, so being killed mid-write leaves the old one intact.
        tmp = self.path.with_suffix(".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            # A checkpoint that cannot be written is not worth failing the run over.
            tmp.unlink(missing_ok=True)

    def remove(self):
        self.path.unlink(missing_ok=True)
        self.path.with_suffix(".tmp").unlink(missing_ok=True)
