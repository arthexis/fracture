from __future__ import annotations

from dataclasses import dataclass, field

from obs_plugins.plugins.base import OBSPlugin, PluginContext
from obs_plugins.plugins.edge_detection import EdgeDetectionPlugin


@dataclass(slots=True)
class ScriptState:
    """Lifecycle state for the host script."""

    obs_module: object
    settings: object | None = None


@dataclass(slots=True)
class PluginManager:
    """Coordinates plugins and routes OBS script callbacks."""

    state: ScriptState
    plugins: list[OBSPlugin] = field(default_factory=list)

    @classmethod
    def with_defaults(cls, obs_module: object) -> "PluginManager":
        state = ScriptState(obs_module=obs_module)
        return cls(state=state, plugins=[EdgeDetectionPlugin()])

    def description(self) -> str:
        names = ", ".join(plugin.name for plugin in self.plugins)
        return (
            "Arthexis OBS plugin host. "
            f"Loaded plugins: {names}. "
            "Each plugin contributes properties in this panel."
        )

    def defaults(self, settings: object) -> None:
        self.state.settings = settings
        for plugin in self.plugins:
            plugin.defaults(settings, self.state.obs_module)

    def properties(self) -> object:
        obs = self.state.obs_module
        props = obs.obs_properties_create()
        for plugin in self.plugins:
            group = obs.obs_properties_create()
            plugin.build_properties(group, obs)
            obs.obs_properties_add_group(
                props,
                f"plugin_{plugin.key}",
                plugin.name,
                obs.OBS_GROUP_NORMAL,
                group,
            )
        return props

    def update(self, settings: object) -> None:
        self.state.settings = settings
        for plugin in self.plugins:
            plugin.update(settings, self.state.obs_module)

    def load(self) -> None:
        context = PluginContext(obs_module=self.state.obs_module, settings=self.state.settings)
        for plugin in self.plugins:
            plugin.on_load(context)

    def unload(self) -> None:
        context = PluginContext(obs_module=self.state.obs_module, settings=self.state.settings)
        for plugin in self.plugins:
            plugin.on_unload(context)
