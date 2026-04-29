"""In-process TTL cache with per-namespace metrics (no Redis)."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from copy import deepcopy
from typing import Any

NAMESPACE_RULE_LOOKUP = "rule_lookup"
NAMESPACE_VALIDATION = "validation"

DEFAULT_TTL_RULE_LOOKUP = 120
DEFAULT_TTL_VALIDATION = 60


class TTLCacheService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[float, Any, str]] = {}
        self._hits: dict[str, int] = {NAMESPACE_RULE_LOOKUP: 0, NAMESPACE_VALIDATION: 0}
        self._misses: dict[str, int] = {NAMESPACE_RULE_LOOKUP: 0, NAMESPACE_VALIDATION: 0}
        self._sets: dict[str, int] = {NAMESPACE_RULE_LOOKUP: 0, NAMESPACE_VALIDATION: 0}
        self._invalidations: dict[str, int] = {NAMESPACE_RULE_LOOKUP: 0, NAMESPACE_VALIDATION: 0}

    def _ns(self, key: str) -> str:
        if ":" not in key:
            return ""
        ns, _, _rest = key.partition(":")
        return ns

    def _bump_miss_key(self, key: str) -> None:
        ns = self._ns(key)
        if ns:
            self._misses.setdefault(ns, 0)
            self._misses[ns] += 1

    def get(self, key: str) -> Any:
        """Return a deepcopied cached value or None (expired counts as miss)."""
        now = time.monotonic()
        with self._lock:
            tup = self._entries.get(key)
            if tup is None:
                self._bump_miss_key(key)
                return None
            expiry, val, _ns_tag = tup
            if expiry < now:
                del self._entries[key]
                ns = self._ns(key)
                if ns:
                    self._misses.setdefault(ns, 0)
                    self._misses[ns] += 1
                return None
            ns_h = self._ns(key)
            if ns_h:
                self._hits.setdefault(ns_h, 0)
                self._hits[ns_h] += 1
            return deepcopy(val)

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store ``value`` until ``ttl_seconds`` from now."""
        now = time.monotonic()
        ns_tag = self._ns(key)
        with self._lock:
            self._entries[key] = (now + max(1, ttl_seconds), value, ns_tag)
            if ns_tag:
                self._sets.setdefault(ns_tag, 0)
                self._sets[ns_tag] += 1

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._entries:
                del self._entries[key]

    def clear_namespace(self, namespace: str) -> None:
        prefix = f"{namespace}:"
        with self._lock:
            to_del = [k for k in self._entries if k.startswith(prefix)]
            for k in to_del:
                del self._entries[k]
            self._invalidations.setdefault(namespace, 0)
            self._invalidations[namespace] += len(to_del)

    def clear_all(self) -> None:
        with self._lock:
            counts: dict[str, int] = {}
            for k in list(self._entries.keys()):
                ns = self._ns(k)
                if ns:
                    counts[ns] = counts.get(ns, 0) + 1
            self._entries.clear()
            for ns, n in counts.items():
                self._invalidations.setdefault(ns, 0)
                self._invalidations[ns] += n

    def invalidate_rule_caches(self) -> None:
        """Heavyweight invalidation when rules or ingestion-affecting data changes."""
        self.clear_namespace(NAMESPACE_RULE_LOOKUP)
        self.clear_namespace(NAMESPACE_VALIDATION)

    def stats(self) -> dict[str, dict[str, int]]:
        with self._lock:
            counts: dict[str, int] = {}
            for k in self._entries:
                ns = self._ns(k)
                if ns:
                    counts[ns] = counts.get(ns, 0) + 1

        base_ns = [NAMESPACE_RULE_LOOKUP, NAMESPACE_VALIDATION]

        def pack(ns: str) -> dict[str, int]:
            return {
                "hits": int(self._hits.get(ns, 0)),
                "misses": int(self._misses.get(ns, 0)),
                "sets": int(self._sets.get(ns, 0)),
                "invalidations": int(self._invalidations.get(ns, 0)),
                "current_size": int(counts.get(ns, 0)),
            }

        return {ns: pack(ns) for ns in base_ns}


_cache = TTLCacheService()


def default_cache() -> TTLCacheService:
    return _cache


def stable_canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_key(namespace: str, digest_hex: str) -> str:
    """Key format ``<namespace>:<hash>`` (hash hex digest contains no colon)."""
    return f"{namespace}:{digest_hex}"


def invalidate_enforcement_caches() -> None:
    """Public hook to clear rule lookup + submission validation caches."""
    default_cache().invalidate_rule_caches()
