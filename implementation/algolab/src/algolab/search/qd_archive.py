"""Quality-diversity (MAP-Elites style) archive for Protocol 238.

A deterministic, serializable archive of behavioural elites.  Each entry is keyed
by a discretised behavioural descriptor and stores the highest-quality
incumbent for that cell.  Novelty is measured as descriptor distance and the
archive can be queried by quality / novelty / predicate (the "selection rule
as a query" interface from AgentDiscover).

No LLM, no randomness, no external dependencies beyond the standard library.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

QD_ARCHIVE_VERSION = "1.0.0"


def cost_tier(cost: float, thresholds: tuple[float, ...] = (10.0, 30.0)) -> int:
    """Ordinal cost tier for a nominal credit cost (deterministic)."""
    tier = 0
    for threshold in thresholds:
        if cost >= threshold:
            tier += 1
        else:
            break
    return tier


def _numeric(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_tuple(descriptor: Any) -> tuple[Any, ...]:
    if isinstance(descriptor, tuple):
        return descriptor
    if isinstance(descriptor, list):
        return tuple(descriptor)
    if isinstance(descriptor, str):
        return (descriptor,)
    return (descriptor,)


def bin_descriptor(descriptor: Any) -> tuple[Any, ...]:
    """Deterministic bin key for a behavioural descriptor.

    Floats are rounded to a stable precision so MAP-Elites cells are stable;
    all other values are preserved verbatim (they must be hashable).
    """
    out: list[Any] = []
    for value in _as_tuple(descriptor):
        if isinstance(value, bool):
            out.append(int(value))
        elif isinstance(value, float):
            out.append(round(value, 6))
        elif isinstance(value, (list, tuple)):
            out.append(bin_descriptor(value))
        else:
            out.append(value)
    return tuple(out)


def behavior_descriptor(
    cost_tier_value: int,
    family_affinities: Iterable[float],
    outcome_stats: Iterable[Any],
) -> tuple[Any, ...]:
    """Build the canonical Protocol-238 descriptor (tuple, hashable).

    cost_tier_value : ordinal cost bucket (int)
    family_affinities : performance vector across families (floats)
    outcome_stats : simple outcome-statistic embedding (Any -> str-ish stable)
    """
    affinities = tuple(round(float(x), 6) for x in family_affinities)
    stats = tuple(
        (round(float(x), 6) if isinstance(x, (int, float)) and not
         isinstance(x, bool) else x)
        for x in outcome_stats
    )
    return (int(cost_tier_value), affinities, stats)


def _euclidean(a: tuple[Any, ...], b: tuple[Any, ...]) -> float:
    # Flatten one level and align lengths; non-numeric -> 0.
    flat_a: list[Any] = []
    flat_b: list[Any] = []
    for x in a:
        if isinstance(x, (tuple, list)):
            flat_a.extend(x)
        else:
            flat_a.append(x)
    for x in b:
        if isinstance(x, (tuple, list)):
            flat_b.extend(x)
        else:
            flat_b.append(x)
    n = max(len(flat_a), len(flat_b))
    total = 0.0
    for i in range(n):
        xa = _numeric(flat_a[i]) if i < len(flat_a) else 0.0
        xb = _numeric(flat_b[i]) if i < len(flat_b) else 0.0
        total += (xa - xb) ** 2
    return math.sqrt(total)


@dataclass(frozen=True)
class QDEntry:
    """One MAP-Elites cell incumbent."""

    entry_id: str
    descriptor: tuple[Any, ...]
    cell: tuple[Any, ...]
    quality: float
    novelty: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "descriptor": list(self.descriptor),
            "cell": list(self.cell),
            "quality": self.quality,
            "novelty": self.novelty,
            "metadata": dict(self.metadata),
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QDEntry:
        return cls(
            entry_id=str(data["entry_id"]),
            descriptor=bin_descriptor(data.get("descriptor", ())),
            cell=bin_descriptor(data.get("cell", data.get("descriptor", ()))),
            quality=float(data.get("quality", 0.0)),
            novelty=float(data.get("novelty", 0.0)),
            metadata=dict(data.get("metadata", {}) or {}),
            payload=dict(data.get("payload", {}) or {}),
        )


class QDArchive:
    """Deterministic MAP-Elites archive. No randomness, stdlib only."""

    def __init__(
        self,
        *,
        version: str = QD_ARCHIVE_VERSION,
        novelty_weight: float = 0.25,
    ):
        self.version = version
        self.novelty_weight = float(novelty_weight)
        self._cells: dict[tuple[Any, ...], QDEntry] = {}

    # -- core MAP-Elites operations --------------------------------------

    @property
    def size(self) -> int:
        return len(self._cells)

    def cells(self) -> dict[tuple[Any, ...], QDEntry]:
        return dict(self._cells)

    def entries(self) -> list[QDEntry]:
        return sorted(
            self._cells.values(),
            key=lambda e: (-e.quality, e.entry_id),
        )

    def get(self, entry_id: str) -> QDEntry | None:
        for entry in self._cells.values():
            if entry.entry_id == entry_id:
                return entry
        return None

    def contains(self, entry_id: str) -> bool:
        return self.get(entry_id) is not None

    def cell_for(self, descriptor: Any) -> tuple[Any, ...]:
        return bin_descriptor(descriptor)

    def novelty(self, descriptor: Any) -> float:
        """Distance to the nearest archived descriptor (1.0 if empty)."""
        if not self._cells:
            return 1.0
        binned = bin_descriptor(descriptor)
        distances = [_euclidean(binned, entry.descriptor)
                     for entry in self._cells.values()]
        return float(min(distances)) if distances else 1.0

    def is_novel_cell(self, descriptor: Any) -> bool:
        return bin_descriptor(descriptor) not in self._cells

    def insert(
        self,
        entry_id: str,
        descriptor: Any,
        quality: float,
        *,
        metadata: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        novelty: float | None = None,
    ) -> bool:
        """MAP-Elites insertion. Returns True iff the entry replaced the
        incumbent of its cell.
        """
        binned = bin_descriptor(descriptor)
        quality = float(quality)
        nov = float(self.novelty(descriptor) if novelty is None else novelty)
        incumbent = self._cells.get(binned)
        if (incumbent is None or quality > incumbent.quality
                or (quality == incumbent.quality
                    and entry_id < incumbent.entry_id)):
            self._cells[binned] = QDEntry(
                entry_id=str(entry_id),
                descriptor=binned,
                cell=binned,
                quality=quality,
                novelty=nov,
                metadata=dict(metadata or {}),
                payload=dict(payload or {}),
            )
            return True
        return False

    def query(
        self,
        *,
        min_quality: float | None = None,
        min_novelty: float | None = None,
        top_k: int | None = None,
        predicate: Callable[[QDEntry], bool] | None = None,
    ) -> list[QDEntry]:
        """Selection rule as query: filter + rank by quality then novelty."""
        result = []
        for entry in self._cells.values():
            if min_quality is not None and entry.quality < min_quality:
                continue
            if min_novelty is not None and entry.novelty < min_novelty:
                continue
            if predicate is not None and not predicate(entry):
                continue
            result.append(entry)
        result.sort(key=lambda e: (-e.quality - self.novelty_weight * e.novelty,
                                    e.entry_id))
        if top_k is not None:
            result = result[: max(0, int(top_k))]
        return result

    def best(self, *, top_k: int = 1) -> list[QDEntry]:
        return self.query(top_k=top_k)

    def high_quality_novel(
        self, *, quality_floor: float | None = None,
    ) -> list[QDEntry]:
        """Entries that are both high-quality and high-novelty (fork parents)."""
        floor = 0.0 if quality_floor is None else float(quality_floor)
        candidates = [e for e in self._cells.values()
                      if e.quality >= floor]
        candidates.sort(key=lambda e: (e.quality + self.novelty_weight * e.novelty,
                                       e.entry_id), reverse=True)
        return candidates

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "novelty_weight": self.novelty_weight,
            "cells": [entry.to_dict() for entry in
                      sorted(self._cells.values(), key=lambda e: e.entry_id)],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QDArchive:
        archive = cls(
            version=str(data.get("version", QD_ARCHIVE_VERSION)),
            novelty_weight=float(data.get("novelty_weight", 0.25)),
        )
        for cell_data in data.get("cells", []):
            entry = QDEntry.from_dict(cell_data)
            archive._cells[entry.cell] = entry
        return archive

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, QDArchive):
            return False
        return self.to_dict() == other.to_dict()

    def __len__(self) -> int:
        return self.size
