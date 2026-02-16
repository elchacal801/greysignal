"""Tamper-evident audit logging for GreySignal operations."""

import os
from typing import Optional

from ..models import AuditEntry
from .logging import get_logger

log = get_logger("audit")

AUDIT_FILE = "data/audit.jsonl"


def _get_last_hash(audit_path: str) -> str:
    """Read the hash of the most recent audit entry, or 'GENESIS' if none."""
    if not os.path.exists(audit_path):
        return "GENESIS"
    try:
        last_line = ""
        with open(audit_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    last_line = stripped
        if not last_line:
            return "GENESIS"
        entry = AuditEntry.model_validate_json(last_line)
        return entry.entry_hash or "GENESIS"
    except Exception as e:
        log.warning(f"Could not read last audit hash: {e}")
        return "UNKNOWN"


def record_audit(
    action: str,
    event_count: int = 0,
    details: str = "",
    actor: str = "system",
    input_hash: Optional[str] = None,
    output_hash: Optional[str] = None,
    audit_path: str = AUDIT_FILE,
) -> AuditEntry:
    """
    Append a tamper-evident audit entry to the audit log.

    Each entry is hash-chained to the previous entry, creating
    a verifiable sequence where tampering is detectable.
    """
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)

    previous_hash = _get_last_hash(audit_path)

    entry = AuditEntry(
        action=action,
        actor=actor,
        input_hash=input_hash,
        output_hash=output_hash,
        event_count=event_count,
        details=details,
        previous_hash=previous_hash,
    ).finalize()

    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")

    log.info(f"Audit: [{action}] {details} (events={event_count}, hash={entry.entry_hash[:12]}...)")
    return entry


def verify_audit_chain(audit_path: str = AUDIT_FILE) -> bool:
    """
    Verify the integrity of the audit chain.

    Returns True if all entries are valid and properly chained.
    """
    if not os.path.exists(audit_path):
        log.info("No audit log found — nothing to verify.")
        return True

    expected_prev = "GENESIS"
    line_num = 0

    with open(audit_path, "r", encoding="utf-8") as f:
        for line in f:
            line_num += 1
            stripped = line.strip()
            if not stripped:
                continue
            try:
                entry = AuditEntry.model_validate_json(stripped)
            except Exception as e:
                log.error(f"Audit line {line_num}: Failed to parse — {e}")
                return False

            # Verify chain link
            if entry.previous_hash != expected_prev:
                log.error(
                    f"Audit line {line_num}: Chain broken. "
                    f"Expected prev={expected_prev[:12]}..., got={entry.previous_hash[:12]}..."
                )
                return False

            # Verify self-hash
            computed = entry.compute_entry_hash()
            if entry.entry_hash != computed:
                log.error(
                    f"Audit line {line_num}: Entry hash mismatch. "
                    f"Stored={entry.entry_hash[:12]}..., computed={computed[:12]}..."
                )
                return False

            expected_prev = entry.entry_hash

    log.info(f"Audit chain verified: {line_num} entries, all valid.")
    return True
