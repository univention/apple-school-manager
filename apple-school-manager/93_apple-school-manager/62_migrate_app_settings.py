#!/usr/share/ucs-test/runner python3
## desc: test migrating the former app settings to the connections file
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [56486]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import json
import os
import stat
import tempfile
from pathlib import Path

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
from univention.asm import config
from univention.config_registry import ConfigRegistry, handler_set
from univention.testing import utils


def main() -> None:
    username = uts.random_username()
    with ucr_test.UCSTestConfigRegistry(), tempfile.TemporaryDirectory() as tmp_dir:
        config.CONFIG_FILE_PATH = os.path.join(tmp_dir, "asm-connections.json")
        handler_set([f"asm/username={username}", "asm/school_whitelist=gym123, ,gs456"])

        if not config.migrate_app_settings():
            utils.fail("migrate_app_settings() did not migrate the app settings.")
        with open(config.CONFIG_FILE_PATH) as fp:
            migrated = json.load(fp)
        expected = [
            {
                "username": username,
                "password_file": "/etc/asm.secret",
                "school_whitelist": ["gym123", "gs456"],
            },
        ]
        if migrated != expected:
            utils.fail(f"Migrated {migrated!r}, expected {expected!r}.")
        mode = stat.S_IMODE(Path(config.CONFIG_FILE_PATH).stat().st_mode)
        if mode != 0o600:
            utils.fail(f"{config.CONFIG_FILE_PATH} has mode {mode:o}, expected 600.")

        ucr = ConfigRegistry()
        ucr.load()
        for key in ("asm/username", "asm/school_whitelist"):
            if ucr.get(key) is not None:
                utils.fail(f"{key} is still set to {ucr.get(key)!r}.")

        handler_set([f"asm/username={uts.random_username()}"])
        if config.migrate_app_settings():
            utils.fail("migrate_app_settings() overwrote an existing connections file.")
        with open(config.CONFIG_FILE_PATH) as fp:
            if json.load(fp) != expected:
                utils.fail("An existing connections file was modified.")


if __name__ == "__main__":
    main()
