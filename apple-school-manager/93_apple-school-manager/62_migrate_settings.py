#!/usr/share/ucs-test/runner python3
## desc: test migrating the former app settings and UCR variables to the settings file
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
    ucr_values = {
        "asm/username": username,
        "asm/school_whitelist": "gym123, ,gs456",
        "asm/attributes/user/email/prepend_domain": "apple",
        "asm/attributes/student/anonymize": "yes",
        "asm/attributes/student/anonymize/first_name": "%uid",
        "asm/attributes/student/anonymize/last_name": "-",
        "asm/attributes/staff/anonymize": "no",
        "asm/attributes/staff/person_id/mapping": "%entryUUID",
        "asm/attributes/student/password_policy": "-",
        "asm/attributes/classes/class_number_empty": "false",
        "asm/ldap_filter/students": "(objectClass=*)",
        "asm/ldap_filter/students/gym123": "(uid=a*)",
        "asm/ldap_filter/staff/rs789": "(uid=b*)",
    }
    expected = {
        "accounts": {
            "default": {"username": username, "password_file": "/etc/asm.secret"},
        },
        "defaults": {
            "email_prepend_domain": "apple",
            "class_number_empty": False,
            "student": {
                "anonymize": True,
                "anonymize_values": {"first_name": "%uid", "last_name": "-"},
                "password_policy": None,
                "ldap_filter": "(objectClass=*)",
            },
            "staff": {"anonymize": False, "person_id_attribute": "entryUUID"},
        },
        "schools": {
            "gym123": {"account": "default", "student": {"ldap_filter": "(uid=a*)"}},
            "gs456": {"account": "default"},
        },
    }
    with ucr_test.UCSTestConfigRegistry(), tempfile.TemporaryDirectory() as tmp_dir:
        config.CONFIG_FILE_PATH = os.path.join(tmp_dir, "asm-connections.json")
        handler_set([f"{key}={value}" for key, value in ucr_values.items()] + ["asm/store_zip=yes"])

        if not config.write_initial_config():
            utils.fail("write_initial_config() did not create the file.")
        with open(config.CONFIG_FILE_PATH) as fp:
            migrated = json.load(fp)
        if migrated != expected:
            utils.fail(f"Migrated\n{migrated!r}\nexpected\n{expected!r}.")
        mode = stat.S_IMODE(Path(config.CONFIG_FILE_PATH).stat().st_mode)
        if mode != 0o600:
            utils.fail(f"{config.CONFIG_FILE_PATH} has mode {mode:o}, expected 600.")

        ucr = ConfigRegistry()
        ucr.load()
        for key in ucr_values:
            if ucr.get(key) is not None:
                utils.fail(f"{key} is still set to {ucr.get(key)!r}.")
        if not ucr.is_true("asm/store_zip"):
            utils.fail("asm/store_zip is an app setting and must not be migrated.")

        password_file = os.path.join(tmp_dir, "asm.secret")
        with open(password_file, "w") as fp:
            fp.write("secret")
        migrated["accounts"]["default"]["password_file"] = password_file
        [connection] = config.parse_config(migrated)
        if connection.settings.school("gym123").student_ldap_filter != "(uid=a*)":
            utils.fail(f"Wrong settings for gym123: {connection.settings.school('gym123')!r}.")
        if connection.settings.school("gs456").student_ldap_filter != "(objectClass=*)":
            utils.fail(f"Wrong settings for gs456: {connection.settings.school('gs456')!r}.")
        if connection.settings.includes("rs789"):
            utils.fail("rs789 was not on the school list and must not be synchronized.")

        handler_set([f"asm/username={uts.random_username()}"])
        if config.write_initial_config():
            utils.fail("write_initial_config() overwrote an existing file.")
        with open(config.CONFIG_FILE_PATH) as fp:
            if json.load(fp) != expected:
                utils.fail("An existing file was modified.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        config.CONFIG_FILE_PATH = os.path.join(tmp_dir, "asm-connections.json")
        data, migrated_keys = config.config_from_ucr({})
        if data != {"accounts": {}, "defaults": {}, "schools": {}} or migrated_keys:
            utils.fail(f"Fresh installation got {data!r}, {migrated_keys!r}.")


if __name__ == "__main__":
    main()
