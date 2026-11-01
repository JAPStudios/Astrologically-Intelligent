"""Plugin discovery and lifecycle for installed Python distributions."""
from __future__ import annotations

import importlib.metadata
import logging
from typing import Any

log = logging.getLogger(__name__)


class PluginManager:
    """Loads explicitly installed entry points; plugins are executable trusted code."""

    GROUP = "astrologically_intelligent.plugins"

    def __init__(self, registry: Any):
        self.registry = registry
        self.loaded: list[dict[str, str]] = []
        self.errors: list[dict[str, str]] = []

    def discover(self) -> list[dict[str, str]]:
        found = []
        for point in importlib.metadata.entry_points(group=self.GROUP):
            found.append({"name": point.name, "value": point.value, "distribution": point.dist.name if point.dist else ""})
        return found

    def load_all(self) -> list[dict[str, str]]:
        self.loaded, self.errors = [], []
        for point in importlib.metadata.entry_points(group=self.GROUP):
            try:
                plugin = point.load()
                setup = getattr(plugin, "setup", None)
                if not callable(setup):
                    raise TypeError("Plugin entry point must expose callable setup(registry)")
                setup(self.registry)
                self.loaded.append({"name": point.name, "distribution": point.dist.name if point.dist else ""})
            except Exception as exc:
                log.exception("Plugin %s failed to load", point.name)
                self.errors.append({"name": point.name, "error": str(exc)})
        return self.status()

    def status(self) -> dict[str, list[dict[str, str]]]:
        return {"loaded": list(self.loaded), "errors": list(self.errors)}
