"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    pass


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    _ensure_workgroup_world()
    _ensure_agent_bridge_delivery()


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass



def _ensure_agent_bridge_delivery():
    """
    Keep the deterministic console-agent response relay available in-game.
    """
    from evennia.utils import create, logger
    from evennia.utils.search import search_script

    try:
        scripts = search_script("agent_bridge_delivery", exact=True)
        if scripts:
            script = scripts[0]
            if not script.is_active:
                script.start()
            return
        create.create_script(
            "typeclasses.scripts.AgentBridgeDeliveryScript",
            key="agent_bridge_delivery",
            interval=2,
            persistent=True,
        )
    except Exception:
        logger.log_trace()


def _ensure_workgroup_world():
    """
    Keep The Workgroup starting area and Intercal body available in-game.
    """
    from world.workgroup_start import ensure_workgroup_world_safe

    ensure_workgroup_world_safe()


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
