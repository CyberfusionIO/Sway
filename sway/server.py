"""TCP server."""

import logging
import socket
from multiprocessing.connection import Connection
from typing import List, Optional

from sway.checks import Check, CheckNotExistsError
from sway.config import Config
from sway.haproxy import Response
from sway.runner import TIMEOUT_COMMAND

TIMEOUT_SOCKET = TIMEOUT_COMMAND + 1

ENABLED_SYSTEMD = True

try:
    import sdnotify
    from systemd.journal import JournalHandler
except ImportError:
    ENABLED_SYSTEMD = False

root_logger = logging.getLogger()
root_logger.propagate = False
root_logger.setLevel(logging.DEBUG)

if ENABLED_SYSTEMD:
    root_logger.addHandler(JournalHandler())

logger = logging.getLogger(__name__)


config = Config()


def get_checks_from_data(data: str) -> List[Check]:
    """Get checks objects from TCP request data."""
    return [
        config.get_check_by_name(name=check_name)
        for check_name in data.split(",")
    ]


def serve(
    multiprocessing_connection: Optional[Connection] = None,  # For tests
) -> None:
    """Serve TCP requests."""
    with socket.socket(
        socket.AF_INET6 if ":" in config.server_host else socket.AF_INET,
        socket.SOCK_STREAM,
    ) as server_socket:
        server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )  # Don't wait for TIME_WAIT expire
        server_socket.bind((config.server_host, config.server_port))
        server_socket.listen(config.server_max_connections)

        if ENABLED_SYSTEMD:
            sdnotify.SystemdNotifier().notify("READY=1")

        if multiprocessing_connection:
            multiprocessing_connection.send("Ready")

        while True:
            try:
                client_socket, client_address = server_socket.accept()

                with client_socket:
                    client_socket.settimeout(TIMEOUT_SOCKET)

                    logger.info("%s Established connection", client_address)

                    data = client_socket.recv(1024).decode("utf-8").rstrip()

                    response = str(Response(checks=get_checks_from_data(data)))

                    logger.info(
                        "%s Sending back response '%s'...",
                        client_address,
                        response.rstrip(),
                    )
                    client_socket.sendall(response.encode("utf-8"))
            except CheckNotExistsError:
                logger.warning(
                    "%s Requested non-existent check, not sending back response",
                    client_address,
                )
            except socket.timeout:
                logger.warning(
                    "%s Did not receive data in %s seconds",
                    client_address,
                    TIMEOUT_SOCKET,
                )
            except ConnectionResetError:
                logger.warning(
                    """%s Connection reset by peer.

Most common cause: HAProxy reset the connection to run another agent check. Sometimes, this happens before 'agent-inter' is reached.

Possible solutions:

- Ensure that 'agent-send' is set. Otherwise, Sway waits for data for TIMEOUT_SOCKET. HAProxy may reset the connection in the meantime.
- Increase 'agent-inter'. This increases chances that HAProxy doesn't reset the connection while an agent check is running.
""",
                    client_address,
                )
