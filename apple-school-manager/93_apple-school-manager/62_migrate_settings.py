#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test migrating the former app settings and UCR variables to the settings file
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [56486]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import json
import stat
from pathlib import Path
from typing import Any

import pytest
import univention.testing.strings as uts
from univention.asm import config
from univention.config_registry import ConfigRegistry
from univention.testing.ucr import UCSTestConfigRegistry


def legacy_ucr_values(username: str) -> dict[str, str]:
    return {
        "asm/username": username,
        "asm/school_whitelist": "gym123, ,gs456",
        "asm/attributes/user/email/prepend_domain": "apple",
        "asm/attributes/student/anonymize": "yes",
        "asm/attributes/student/anonymize/first_name": "%uid",
        "asm/attributes/student/anonymize/last_name": "-",
        "asm/attributes/student/anonymize/sis_username": "",
        "asm/attributes/staff/anonymize": "no",
        "asm/attributes/staff/anonymize/first_name": "%givenName",
        "asm/attributes/staff/anonymize/last_name": "%sn",
        "asm/attributes/staff/anonymize/sis_username": "%uid",
        "asm/attributes/staff/person_id/mapping": "%entryUUID",
        "asm/attributes/student/password_policy": "-",
        "asm/attributes/classes/class_number_empty": "false",
        "asm/ldap_filter/students": "(objectClass=*)",
        "asm/ldap_filter/students/gym123": "(uid=a*)",
        "asm/ldap_filter/staff/rs789": "(uid=b*)",
    }


def expected_settings(username: str) -> dict[str, Any]:
    return {
        "accounts": {
            "default": {"username": username, "password_file": "/etc/asm.secret"},
        },
        "defaults": {
            "email_prepend_domain": "apple",
            "class_number_empty": False,
            "student": {
                "anonymize": True,
                "anonymize_values": {"first_name": "%uid", "last_name": "-", "sis_username": None},
                "password_policy": None,
                "ldap_filter": "(objectClass=*)",
            },
            "staff": {
                "anonymize": False,
                "anonymize_values": {
                    "first_name": "%givenName",
                    "last_name": "%sn",
                    "sis_username": "%uid",
                },
                "person_id_attribute": "entryUUID",
            },
        },
        "schools": {
            "gym123": {"account": "default", "student": {"ldap_filter": "(uid=a*)"}},
            "gs456": {"account": "default"},
        },
    }


@pytest.fixture
def config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "asm-connections.json"
    monkeypatch.setattr(config, "CONFIG_FILE_PATH", str(path))
    return path


@pytest.fixture
def username(ucr: UCSTestConfigRegistry) -> str:
    username: str = uts.random_username()
    ucr.handler_set(
        [f"{key}={value}" for key, value in legacy_ucr_values(username).items()] + ["asm/store_zip=yes"]
    )
    return username


@pytest.fixture
def migrated(config_file: Path, username: str) -> dict[str, Any]:  # noqa: ARG001
    assert config.write_initial_config()
    data: dict[str, Any] = json.loads(config_file.read_text())
    return data


def test_migration_writes_settings_file(migrated: dict[str, Any], username: str) -> None:
    assert migrated == expected_settings(username)


def test_settings_file_is_only_readable_by_root(migrated: dict[str, Any], config_file: Path) -> None:  # noqa: ARG001
    assert stat.S_IMODE(config_file.stat().st_mode) == 0o600


def test_migration_unsets_ucr_variables(migrated: dict[str, Any], username: str) -> None:  # noqa: ARG001
    ucr = ConfigRegistry()
    ucr.load()
    assert {key: ucr[key] for key in legacy_ucr_values(username) if ucr.get(key) is not None} == {}
    assert ucr.is_true("asm/store_zip"), "asm/store_zip is an app setting and must not be migrated."


def test_migrated_settings_apply_per_school(migrated: dict[str, Any], tmp_path: Path) -> None:
    password_file = tmp_path / "asm.secret"
    password_file.write_text("secret")
    migrated["accounts"]["default"]["password_file"] = str(password_file)
    [connection] = config.parse_config(migrated)
    assert connection.settings.school("gym123").student_ldap_filter == "(uid=a*)"
    assert connection.settings.school("gs456").student_ldap_filter == "(objectClass=*)"
    assert not connection.settings.includes("rs789")


def test_existing_file_is_not_overwritten(
    migrated: dict[str, Any], config_file: Path, username: str, ucr: UCSTestConfigRegistry
) -> None:
    ucr.handler_set([f"asm/username={uts.random_username()}"])
    assert not config.write_initial_config()
    assert json.loads(config_file.read_text()) == migrated == expected_settings(username)


def test_fresh_installation_migrates_nothing() -> None:
    assert config.config_from_ucr({}) == ({"accounts": {}, "defaults": {}, "schools": {}}, set())
