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


def test_misspelled_school_is_rejected_with_catch_all(password_file: str) -> None:
    connections = config.parse_config(
        settings_file(password_file, ["north", "south"], {"gym1234": "north", "*": "south"}),
    )
    with pytest.raises(config.ASMConfigError, match="gym1234"):
        config.check_schools(connections, ["gym123", "gs456"])


def test_unknown_school_without_catch_all_is_skipped(
    password_file: str, caplog: pytest.LogCaptureFixture
) -> None:
    connections = config.parse_config(
        settings_file(
            password_file,
            ["north", "south"],
            {"gym123": "north", "gone": "north", "gone2": "south"},
        ),
    )
    receiving = config.check_schools(connections, ["gym123", "gs456"])
    assert [connection.name for connection in receiving] == ["north"]
    assert "'gone'" in caplog.text
    assert "'gone2'" in caplog.text
    assert "'south' has no existing school" in caplog.text


def test_no_account_with_an_existing_school_is_rejected(password_file: str) -> None:
    connections = config.parse_config(settings_file(password_file, ["north"], {"gone": "north"}))
    with pytest.raises(config.ASMConfigError, match="receives an existing school"):
        config.check_schools(connections, ["gym123", "gs456"])


@pytest.mark.parametrize("name", ["north", "school-1", "a_b.c"])
def test_valid_account_name(password_file: str, name: str) -> None:
    [connection] = config.parse_config(settings_file(password_file, [name], {"*": name}))
    assert connection.name == name


@pytest.mark.parametrize("name", ["north/south", "north south", "north=south", "Nord-Süd"])
def test_invalid_account_name(password_file: str, name: str) -> None:
    with pytest.raises(config.ASMConfigError, match="account name"):
        config.parse_config(settings_file(password_file, [name], {"*": name}))


def test_location_mapping(password_file: str) -> None:
    data = settings_file(password_file, ["north"], {"gym123": "north", "gs456": "north", "*": "north"})
    data["schools"]["gym123"].update({"location_id": "4711", "location_name": "Gymnasium Musterstadt"})
    data["schools"]["gs456"]["location_name"] = "Grundschule Musterstadt"
    [connection] = config.parse_config(data)
    config.check_schools([connection], ["gym123", "gs456", "rs789"])
    settings = connection.settings
    assert settings.location_id("gym123") == "4711"
    assert settings.school("gym123").location_name == "Gymnasium Musterstadt"
    assert settings.location_id("gs456") == "gs456"
    assert settings.school("gs456").location_name == "Grundschule Musterstadt"
    assert settings.location_id("rs789") == "rs789"
    assert settings.school("rs789").location_name is None


@pytest.mark.parametrize("key", ["location_id", "location_name"])
def test_location_mapping_rejected_for_other_schools(password_file: str, key: str) -> None:
    data = settings_file(password_file, ["north"], {"*": "north"})
    data["schools"]["*"][key] = "4711"
    with pytest.raises(config.ASMConfigError, match=key):
        config.parse_config(data)


@pytest.mark.parametrize("key", ["location_id", "location_name"])
def test_location_mapping_rejected_in_defaults(password_file: str, key: str) -> None:
    data = settings_file(password_file, ["north"], {"*": "north"})
    data["defaults"] = {key: "4711"}
    with pytest.raises(config.ASMConfigError, match=key):
        config.parse_config(data)


@pytest.mark.parametrize(
    ("key", "value"),
    [("location_id", ""), ("location_id", "47 11"), ("location_name", " "), ("location_id", 4711)],
)
def test_invalid_location_mapping(password_file: str, key: str, value: object) -> None:
    data = settings_file(password_file, ["north"], {"gym123": "north"})
    data["schools"]["gym123"][key] = value
    with pytest.raises(config.ASMConfigError, match=key):
        config.parse_config(data)


@pytest.mark.parametrize(
    ("schools", "location_ids"),
    [
        ({"gym123": "north", "gs456": "north"}, {"gym123": "4711", "gs456": "4711"}),
        ({"gym123": "north", "gs456": "north"}, {"gym123": "gs456"}),
        ({"gym123": "north", "*": "north"}, {"gym123": "rs789"}),
    ],
)
def test_duplicate_location_id_is_rejected(
    password_file: str, schools: dict[str, str], location_ids: dict[str, str]
) -> None:
    data = settings_file(password_file, ["north"], schools)
    for school, location_id in location_ids.items():
        data["schools"][school]["location_id"] = location_id
    connections = config.parse_config(data)
    with pytest.raises(config.ASMConfigError, match="same location_id"):
        config.check_schools(connections, ["gym123", "gs456", "rs789"])


def test_same_location_id_in_different_accounts(password_file: str) -> None:
    data = settings_file(password_file, ["north", "south"], {"gym123": "north", "gs456": "south"})
    data["schools"]["gym123"]["location_id"] = "4711"
    data["schools"]["gs456"]["location_id"] = "4711"
    connections = config.parse_config(data)
    assert len(config.check_schools(connections, ["gym123", "gs456"])) == 2
