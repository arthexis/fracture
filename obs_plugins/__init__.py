"""Arthexis OBS plugin host package."""

__all__ = ["PluginManager", "ScriptState"]


def __getattr__(name: str):
    if name in __all__:
        from .core import PluginManager, ScriptState

        return {"PluginManager": PluginManager, "ScriptState": ScriptState}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
