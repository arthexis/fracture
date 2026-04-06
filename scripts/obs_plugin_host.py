"""OBS script entrypoint for the Arthexis multi-plugin host."""

from __future__ import annotations

import obspython as obs

from obs_plugins.core import PluginManager

_MANAGER = PluginManager.with_defaults(obs)


def script_description() -> str:
    return _MANAGER.description()


def script_defaults(settings) -> None:
    _MANAGER.defaults(settings)


def script_properties():
    return _MANAGER.properties()


def script_update(settings) -> None:
    _MANAGER.update(settings)


def script_load(settings) -> None:
    _MANAGER.state.settings = settings
    _MANAGER.load()


def script_unload() -> None:
    _MANAGER.unload()
