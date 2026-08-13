"""Skill registry: the M4 cooperative layer (MASTER_SPEC.md §3.4, §8.3).

A registry declares which agent fills which operator role for a task, what
it is allowed to produce (its ``record_target``, i.e. the directory it may
commit evidence into), and its last-known-good job id. Registrations are
append-only lines in ``artifacts/registry/registry.tsv``; the *current*
role mapping is the most recent line per agent.

Checks against the registry gate the building blocks:

- a plan may only use an operator if the responsible agent is registered
  with a role that may invoke that operator;
- a proposal's target (``<operator>-...``) must match the operator the
  plan declared;
- the cooperative runtime will only execute proposals produced by agents
  that are registered for the task.

Skills are validated against the operator catalog (role must be in
``M4_OPERATOR_ROLES``) so an unregistered role can never gate execution.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from ..util import utc_now
from .operators import M4_OPERATOR_ROLES, OPERATOR_ELIGIBILITY

_TSV_FIELDS = (
    "agent",
    "role",
    "status",
    "last_known_good_job_id",
    "record_target",
    "updated_at",
)
_TSV_LINE = re.compile(r"^(?P<agent>[^|\t]+)\t(?P<role>[^|\t]+)\t"
                       r"(?P<status>[^|\t]+)\t(?P<lkg>[^|\t]*)\t"
                       r"(?P<target>[^|\t]*)\t(?P<ts>[^|\t]+)$")
VALID_ROLES = frozenset(M4_OPERATOR_ROLES)


class RegistryError(RuntimeError):
    """Registry file missing, malformed, or a registration is invalid."""


@dataclass(frozen=True)
class RegistryEntry:
    agent: str
    role: str
    status: str
    last_known_good_job_id: str = ""
    record_target: str = ""
    updated_at: str = ""

    def __post_init__(self) -> None:
        if not self.agent or not self.role:
            raise RegistryError("agent and role are required")
        if self.role not in VALID_ROLES:
            raise RegistryError(
                f"role {self.role!r} is not in the M4 operator-role catalog: "
                f"{sorted(VALID_ROLES)}"
            )
        if self.status not in ("active", "suspended"):
            raise RegistryError(
                f"status must be active or suspended, got {self.status!r}"
            )

    def to_tsv(self) -> str:
        return "\t".join(
            (self.agent, self.role, self.status,
             self.last_known_good_job_id or "",
             self.record_target or "",
             self.updated_at or utc_now())
        )


class Registry:
    """Append-only skill registry backed by a TSV file under artifacts."""

    def __init__(self, root: str):
        self._root = root
        self._path = os.path.join(root, "registry", "registry.tsv")

    @property
    def path(self) -> str:
        return self._path

    def _ensure_file(self) -> None:
        d = os.path.dirname(self._path)
        os.makedirs(d, exist_ok=True)
        if not os.path.exists(self._path):
            with open(self._path, "w", encoding="utf-8") as fh:
                fh.write("# " + "\t".join(_TSV_FIELDS) + "\n")

    def register(self, entry: RegistryEntry) -> None:
        """Append *entry*; the most recent line per agent wins."""
        self._ensure_file()
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(entry.to_tsv() + "\n")

    def _lines(self) -> list[tuple[RegistryEntry, int]]:
        self._ensure_file()
        entries: list[tuple[RegistryEntry, int]] = []
        with open(self._path, encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, start=1):
                line = raw.rstrip("\n")
                if not line or line.startswith("#"):
                    continue
                m = _TSV_LINE.match(line)
                if not m:
                    raise RegistryError(
                        f"{self._path}:{lineno}: malformed registry line"
                    )
                try:
                    entries.append((
                        RegistryEntry(
                            agent=m.group("agent"),
                            role=m.group("role"),
                            status=m.group("status"),
                            last_known_good_job_id=m.group("lkg"),
                            record_target=m.group("target"),
                            updated_at=m.group("ts"),
                        ),
                        lineno,
                    ))
                except RegistryError as exc:
                    raise RegistryError(
                        f"{self._path}:{lineno}: {exc}"
                    ) from exc
        return entries

    def current(self) -> dict[str, RegistryEntry]:
        """Latest registration per agent."""
        current: dict[str, RegistryEntry] = {}
        for entry, _ in self._lines():
            current[entry.agent] = entry
        return current

    def get(self, agent: str) -> RegistryEntry | None:
        return self.current().get(agent)

    def list(self) -> list[RegistryEntry]:
        """All current registrations, ordered by agent name."""
        current = self.current()
        return [current[k] for k in sorted(current)]

    def roles_for(self, agent: str) -> set[str]:
        entry = self.current().get(agent)
        return {entry.role} if entry and entry.status == "active" else set()

    def may_invoke(self, agent: str, operator: str) -> bool:
        """Whether *agent* may invoke *operator* under its registered role."""
        entry = self.current().get(agent)
        if not entry or entry.status != "active":
            return False
        return entry.role in OPERATOR_ELIGIBILITY.get(operator, set())


class CooperativeRegistry(Registry):
    """Registry that also resolves role bundles for the cooperative runner."""

    def operators_for(self, agent: str) -> list[str]:
        entry = self.current().get(agent)
        if not entry or entry.status != "active":
            return []
        return [
            name for name, roles in OPERATOR_ELIGIBILITY.items()
            if entry.role in roles
        ]


def validate_skill_toml(path: str) -> dict[str, object]:
    """Validate a skill TOML's role against the operator catalog.

    Returns the parsed ``[skill]`` section. Raises ``RegistryError`` if the
    role is not a registered M4 operator role.
    """
    import tomllib

    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    skill = data.get("skill")
    if not isinstance(skill, dict) or not skill.get("name"):
        raise RegistryError(f"{path}: missing [skill] table with name")
    role = skill.get("role")
    if role and role not in VALID_ROLES:
        raise RegistryError(
            f"{path}: role {role!r} not in {sorted(VALID_ROLES)}"
        )
    return skill


__all__ = [
    "RegistryError",
    "RegistryEntry",
    "Registry",
    "CooperativeRegistry",
    "validate_skill_toml",
]
