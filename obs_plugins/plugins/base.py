from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class PluginContext:
    """Shared mutable context passed to plugins."""

    obs_module: object
    settings: object | None = None


class OBSPlugin(Protocol):
    """Protocol for plugins that can be hosted by the OBS script entrypoint."""

    name: str
    key: str

    def build_properties(self, props: object, obs: object) -> None:
        ...

    def defaults(self, settings: object, obs: object) -> None:
        ...

    def update(self, settings: object, obs: object) -> None:
        ...

    def on_load(self, context: PluginContext) -> None:
        ...

    def on_unload(self, context: PluginContext) -> None:
        ...
