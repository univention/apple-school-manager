#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test validating the settings file
## tags: [apptest]  # noqa: ERA001
## exposure: safe  # noqa: ERA001
## packages:
##   - python3-univention-apple-school-manager-connector
## bugs: [56486]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path
from typing import Any

import pytest
from univention.asm import config


@pytest.fixture
def password_file(tmp_path: Path) -> str:
    path = tmp_path / "asm.secret"
    path.write_text("secret")
    return str(path)


def settings_file(password_file: str, accounts: list[str], schools: dict[str, str]) -> dict[str, Any]:
    return {
        "accounts": {
            name: {"username": f"sftp-{index}", "password_file": password_file}
            for index, name in enumerate(accounts)
        },
        "schools": {school: {"account": account} for school, account in schools.items()},
    }


def test_existing_schools_pass(password_file: str) -> None:
    connections = config.parse_config(
        settings_file(password_file, ["north", "south"], {"gym123": "north", "*": "south"}),
    )
    config.check_schools(connections, ["gym123", "gs456"])


def test_misspelled_school_is_rejected(password_file: str) -> None:
    connections = config.parse_config(
        settings_file(password_file, ["north", "south"], {"gym1234": "north", "*": "south"}),
    )
    with pytest.raises(config.ASMConfigError, match="gym1234"):
        config.check_schools(connections, ["gym123", "gs456"])
