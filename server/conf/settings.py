r"""
Evennia settings file.

The available options are found in the default settings file found
here:

https://www.evennia.com/docs/latest/Setup/Settings-Default.html

Remember:

Don't copy more from the default file than you actually intend to
change; this will make sure that you don't overload upstream updates
unnecessarily.

When changing a setting requiring a file system path (like
path/to/actual/file.py), use GAME_DIR and EVENNIA_DIR to reference
your game folder and the Evennia library folders respectively. Python
paths (path.to.module) should be given relative to the game's root
folder (typeclasses.foo) whereas paths within the Evennia library
needs to be given explicitly (evennia.foo).

If you want to share your game dir, including its settings, you can
put secret game- or server-specific settings in secret_settings.py.

"""

# Use the defaults from Evennia unless explicitly overridden
from evennia.settings_default import *

######################################################################
# Evennia base server config
######################################################################

# This is the name of your game. Make it catchy!
SERVERNAME = "arthexis"



######################################################################
# Arthexis SSH play-door config
######################################################################
SERVERNAME = "Arthexis Evennia"
LOCKDOWN_MODE = False
NEW_ACCOUNT_REGISTRATION_ENABLED = True
PERMISSION_ACCOUNT_DEFAULT = "Player"
TELNET_ENABLED = True
TELNET_PORTS = [4000]
TELNET_INTERFACES = ["127.0.0.1"]
TELNET_PROTOCOL_CLASS = "server.conf.play_telnet.PlayTelnetProtocol"
SSH_ENABLED = False
WEBSERVER_ENABLED = True
WEBCLIENT_ENABLED = True
WEBSOCKET_CLIENT_ENABLED = True

# Public web play is exposed only through nginx HTTPS. Keep raw Evennia web
# and websocket ports loopback-only.
WEBSERVER_PORTS = [(4001, 4005)]
WEBSERVER_INTERFACES = ["127.0.0.1"]
WEBSOCKET_CLIENT_PORT = 4002
WEBSOCKET_CLIENT_INTERFACE = "127.0.0.1"
WEBSOCKET_CLIENT_URL = "wss://arthexis.com/evennia-websocket/"

# Keep Evennia browser sessions separate from the Arthexis suite login cookie.
SESSION_COOKIE_NAME = "evennia_sessionid"
WORKGROUP_PLAY_SUITE_SESSION_COOKIE_NAME = "sessionid"
WORKGROUP_PLAY_SUITE_SESSION_URL = "http://127.0.0.1:8888/workgroup/play/session/"
ALLOWED_HOSTS = ["arthexis.com", ".arthexis.com", "127.0.0.1", "localhost"]

######################################################################
# Settings given in secret_settings.py override those in this file.
######################################################################
try:
    from server.conf.secret_settings import *
except ImportError:
    print("secret_settings.py file not found or failed to import.")
