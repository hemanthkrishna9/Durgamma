"""Agent Registry — loads and queries the agent role definitions."""

from pathlib import Path
from typing import Any

import yaml

from app.config import settings


class AgentRegistry:
    """Loads agent_registry.yaml and provides lookup methods."""

    def __init__(self, registry_path: str | None = None):
        if registry_path is None:
            registry_path = str(Path(__file__).parent.parent.parent / "agent_registry.yaml")
        self._path = registry_path
        self._data: dict[str, Any] = {}
        self._loaded = False

    def load(self) -> None:
        with open(self._path, "r") as f:
            self._data = yaml.safe_load(f)
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    @property
    def roles(self) -> dict[str, Any]:
        self._ensure_loaded()
        return self._data.get("roles", {})

    def get_role(self, role_key: str) -> dict[str, Any] | None:
        return self.roles.get(role_key)

    def get_always_spawn_roles(self) -> list[str]:
        return [key for key, val in self.roles.items() if val.get("always_spawn")]

    def get_roles_by_category(self, category: str) -> dict[str, Any]:
        return {key: val for key, val in self.roles.items() if val.get("category") == category}

    def get_role_names(self, role_key: str) -> list[str]:
        role = self.get_role(role_key)
        return role.get("names", []) if role else []

    def get_authority_level(self, role_key: str) -> int:
        role = self.get_role(role_key)
        return role.get("authority_level", 50) if role else 50

    def get_domain(self, role_key: str) -> str:
        role = self.get_role(role_key)
        return role.get("domain", "") if role else ""

    def get_model(self, role_key: str) -> str:
        role = self.get_role(role_key)
        return role.get("model", settings.default_model) if role else settings.default_model

    def get_tools(self, role_key: str) -> list[str]:
        role = self.get_role(role_key)
        return role.get("tools", []) if role else []

    def list_all_roles(self) -> list[str]:
        return list(self.roles.keys())

    def get_spawn_conditions(self, role_key: str) -> list[str]:
        role = self.get_role(role_key)
        return role.get("spawn_conditions", []) if role else []

    def to_summary(self) -> list[dict[str, Any]]:
        """Return a summarized list of roles for LLM context."""
        result = []
        for key, role in self.roles.items():
            result.append({
                "role": key,
                "display_name": role.get("display_name", key),
                "category": role.get("category", ""),
                "description": role.get("description", ""),
                "authority_level": role.get("authority_level", 50),
                "domain": role.get("domain", ""),
                "spawn_conditions": role.get("spawn_conditions", []),
            })
        return result


# Singleton instance
registry = AgentRegistry()
