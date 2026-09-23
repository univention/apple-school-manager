# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Configuration of the Apple School Manager connections.
"""

import json
import os
from dataclasses import dataclass
from typing import Any

from univention.config_registry import ConfigRegistry, handler_unset

CONFIG_FILE_PATH = "/etc/asm-connections.json"
LEGACY_PASSWORD_FILE_PATH = "/etc/asm.secret"  # noqa: S105
LEGACY_UCR_USERNAME_KEY = "asm/username"
LEGACY_UCR_OU_WHITELIST_KEY = "asm/school_whitelist"

REQUIRED_KEYS = {"username", "password_file"}
OPTIONAL_KEYS = {"school_whitelist"}


class ASMConfigError(Exception):
    pass


@dataclass(frozen=True)
class Connection:
    username: str
    password: str
    school_whitelist: list[str] | None


def get_connections() -> list[Connection]:
    """
    Return the Apple School Manager connections from :py:data:`CONFIG_FILE_PATH`.

    :raises ASMConfigError: if the file is missing, incomplete or invalid
    """
    if not os.path.exists(CONFIG_FILE_PATH):
        msg = (
            f"No Apple School Manager account configured. Create {CONFIG_FILE_PATH} "
            "as described in the Apple School Manager Connector manual."
        )
        raise ASMConfigError(msg)
    return _connections_from_file(CONFIG_FILE_PATH)


def migrate_app_settings() -> bool:
    """
    Move the account from the former app settings to :py:data:`CONFIG_FILE_PATH`.

    Does nothing if the file already exists or no username was configured.
    The password stays in :py:data:`LEGACY_PASSWORD_FILE_PATH`.

    :return: whether the app settings were migrated
    """
    ucr = ConfigRegistry()
    ucr.load()
    username = ucr.get(LEGACY_UCR_USERNAME_KEY)
    if os.path.exists(CONFIG_FILE_PATH) or not username:
        return False
    entry: dict[str, Any] = {"username": username, "password_file": LEGACY_PASSWORD_FILE_PATH}
    whitelist = [school.strip() for school in ucr.get(LEGACY_UCR_OU_WHITELIST_KEY, "").split(",")]
    whitelist = [school for school in whitelist if school]
    if whitelist:
        entry["school_whitelist"] = whitelist
    fd = os.open(CONFIG_FILE_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as config_file:
        json.dump([entry], config_file, indent=4)
        config_file.write("\n")
    handler_unset([LEGACY_UCR_USERNAME_KEY, LEGACY_UCR_OU_WHITELIST_KEY])
    print(f"Migrated the Apple School Manager app settings to {CONFIG_FILE_PATH}.")
    return True


def _connections_from_file(path: str) -> list[Connection]:
    try:
        with open(path) as config_file:
            entries = json.load(config_file)
    except FileNotFoundError:
        msg = f"Config file {path!r} does not exist."
        raise ASMConfigError(msg)
    except json.JSONDecodeError as exc:
        msg = f"Config file {path!r} is not valid JSON: {exc}"
        raise ASMConfigError(msg)
    if not isinstance(entries, list) or not entries:
        msg = f"Config file {path!r} must contain a non-empty list of connections."
        raise ASMConfigError(msg)
    connections = [_parse_entry(entry, index, path) for index, entry in enumerate(entries)]
    if len(connections) > 1:
        for connection in connections:
            if not connection.school_whitelist:
                msg = (
                    f"Connection {connection.username!r} in {path!r} has no school_whitelist. "
                    "With more than one connection, every connection needs one."
                )
                raise ASMConfigError(msg)
    usernames = [connection.username for connection in connections]
    duplicates = sorted({username for username in usernames if usernames.count(username) > 1})
    if duplicates:
        msg = f"Config file {path!r} lists the username(s) {', '.join(duplicates)} more than once."
        raise ASMConfigError(msg)
    return connections


def _parse_entry(entry: Any, index: int, path: str) -> Connection:  # noqa: ANN401
    where = f"Connection #{index + 1} in {path!r}"
    if not isinstance(entry, dict):
        msg = f"{where} must be a JSON object."
        raise ASMConfigError(msg)
    missing = REQUIRED_KEYS - entry.keys()
    if missing:
        msg = f"{where} is missing {', '.join(sorted(missing))}."
        raise ASMConfigError(msg)
    unknown = entry.keys() - REQUIRED_KEYS - OPTIONAL_KEYS
    if unknown:
        msg = f"{where} has unknown key(s) {', '.join(sorted(unknown))}."
        raise ASMConfigError(msg)
    username = entry["username"]
    password_file = entry["password_file"]
    if not isinstance(username, str) or not username:
        msg = f"{where}: username must be a non-empty string."
        raise ASMConfigError(msg)
    if not isinstance(password_file, str) or not password_file:
        msg = f"{where}: password_file must be a non-empty string."
        raise ASMConfigError(msg)
    whitelist = entry.get("school_whitelist")
    if whitelist is not None and (
        not isinstance(whitelist, list)
        or not all(isinstance(school, str) and school for school in whitelist)
    ):
        msg = f"{where}: school_whitelist must be a list of school abbreviations."
        raise ASMConfigError(msg)
    try:
        password = _read_password(password_file)
    except ASMConfigError as exc:
        msg = f"{where}: {exc}"
        raise ASMConfigError(msg)
    if not password:
        msg = f"{where}: password file {password_file!r} is empty."
        raise ASMConfigError(msg)
    return Connection(username, password, whitelist or None)


def _read_password(path: str) -> str:
    try:
        with open(path) as password_file:
            return password_file.read().strip("\n")
    except FileNotFoundError:
        msg = f"Password file {path!r} does not exist."
        raise ASMConfigError(msg)
