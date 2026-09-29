#!/usr/share/ucs-test/runner python3
## desc: test asm-upload with multiple Apple School Manager accounts and their settings
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [56486]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import contextlib
import csv
import filecmp
import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from types import TracebackType
from typing import Any

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
from paramiko.client import AutoAddPolicy, SSHClient
from ucsschool.lib.models.utils import exec_cmd
from univention.admin.uldap import getMachineConnection
from univention.asm.config import CONFIG_FILE_PATH
from univention.config_registry import handler_set
from univention.testing import utils
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase

PASSWORD = "univention"  # noqa: S105
REMOTE_PATH = "/archive.zip"


class LocalHostAsASM:
    def __init__(self, connections: list[dict[str, Any]], config_dir: str) -> None:
        self.connections = connections
        self.config_dir = config_dir

    def __enter__(self) -> None:
        ucr_values = [
            "hosts/static/127.0.60.60=upload.appleschoolcontent.com",
            "asm/store_zip=yes",
        ]
        ucr_values.extend(f"auth/sshd/user/{c['username']}=yes" for c in self.connections)
        handler_set(ucr_values)
        config: dict[str, Any] = {"accounts": {}, "schools": {}}
        for connection in self.connections:
            password_file = os.path.join(self.config_dir, f"{connection['username']}.secret")
            with open(password_file, "w") as fp:
                fp.write(PASSWORD)
            config["accounts"][connection["username"]] = {
                "username": connection["username"],
                "password_file": password_file,
                **connection["account_settings"],
            }
            config["schools"][connection["school"]] = {
                "account": connection["username"],
                **connection["school_settings"],
            }
        if os.path.exists(CONFIG_FILE_PATH):
            os.rename(CONFIG_FILE_PATH, f"{CONFIG_FILE_PATH}.backup_61test")
        with open(CONFIG_FILE_PATH, "w") as fp:
            json.dump(config, fp)
        os.rename("/etc/asm_public_key", "/etc/asm_public_key.backup_61test")
        for connection in self.connections:
            subprocess.check_call(["mkhomedir_helper", connection["username"]])
            client = SSHClient()
            client.set_missing_host_key_policy(AutoAddPolicy())  # noqa: S507
            client.connect(
                "upload.appleschoolcontent.com",
                username=connection["username"],
                password=PASSWORD,
            )
            sftp = client.open_sftp()
            sftp.chdir(connection["home_dir"])
            sftp.mkdir("dropbox")
            client.save_host_keys("/etc/asm_public_key")
            client.close()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        os.rename("/etc/asm_public_key.backup_61test", "/etc/asm_public_key")
        os.unlink(CONFIG_FILE_PATH)
        if os.path.exists(f"{CONFIG_FILE_PATH}.backup_61test"):
            os.rename(f"{CONFIG_FILE_PATH}.backup_61test", CONFIG_FILE_PATH)
        for connection in self.connections:
            with contextlib.suppress(OSError):
                shutil.rmtree(os.path.join(connection["home_dir"], "dropbox"))


class TempWorldWritableFile:
    def __init__(self, path: str) -> None:
        self.path = path

    def __enter__(self) -> None:
        with open(self.path, "w") as fp:
            print(f"Creating world writable file {self.path!r}...")
            os.fchmod(fp.fileno(), 0o666)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        with contextlib.suppress(OSError):
            print(f"Deleting file {self.path!r}...")
            os.unlink(self.path)


def read_csv(zip_path: str, name: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(zip_path) as zf:
        content = zf.read(name).decode("utf-8")
    return list(csv.DictReader(io.StringIO(content)))


class Test(ImportTestbase):  # type: ignore[misc]
    ou_C = None

    def create_sftp_user(
        self,
        school: str,
        account_settings: dict[str, Any],
        school_settings: dict[str, Any],
    ) -> dict[str, Any]:
        school_class = f"{school}-{uts.random_username()}"
        username, dn = self.schoolenv.create_student(school, classes=school_class, password=PASSWORD)
        lo, _po = getMachineConnection()
        attrs = lo.get(dn, attr=["homeDirectory", "givenName"])
        return {
            "username": username,
            "home_dir": attrs["homeDirectory"][0].decode(),
            "first_name": attrs["givenName"][0].decode(),
            "school": school,
            "school_class": school_class,
            "account_settings": account_settings,
            "school_settings": school_settings,
        }

    def test(self) -> None:
        connections = [
            self.create_sftp_user(self.ou_A.name, {"student": {"anonymize": False}}, {}),
            self.create_sftp_user(
                self.ou_B.name,
                {"student": {"anonymize": True}},
                {"course_name_pattern": "{name}"},
            ),
        ]
        with (
            tempfile.TemporaryDirectory() as config_dir,
            ucr_test.UCSTestConfigRegistry(),
            LocalHostAsASM(connections, config_dir),
            TempWorldWritableFile(REMOTE_PATH),
        ):
            cmd = ["/usr/sbin/asm-upload"]
            print(f"Executing {cmd!r}...")
            returncode, stdout, stderr = exec_cmd(cmd)
            print(f"-> returncode={returncode}")
            print(f"-> stdout={stdout}")
            print(f"-> stderr={stderr}")
            if returncode:
                utils.fail(f"{cmd!r} returned {returncode}.")
            prefix = "The uploaded zip is stored in: "
            zip_paths = [line[len(prefix) :] for line in stderr.split("\n") if line.startswith(prefix)]
            if len(zip_paths) != len(connections):
                utils.fail(f"Expected {len(connections)} uploads, found {len(zip_paths)}.")
            for connection, zip_path in zip(connections, zip_paths, strict=True):
                self.check_archive(connection, zip_path)
            if not filecmp.cmp(zip_paths[-1], REMOTE_PATH, shallow=False):
                utils.fail("Last ZIP file was not correctly uploaded.")

    def check_archive(self, connection: dict[str, Any], zip_path: str) -> None:
        username = connection["username"]
        locations = {row["location_id"] for row in read_csv(zip_path, "locations.csv")}
        print(f"{username}: zip_path={zip_path!r} locations={locations!r}")
        if locations != {connection["school"]}:
            utils.fail(
                f"Archive for {username} contains {locations!r}, expected {connection['school']!r}."
            )

        students = {row["sis_username"]: row for row in read_csv(zip_path, "students.csv")}
        anonymize = connection["account_settings"]["student"]["anonymize"]
        expected_first_name = username if anonymize else connection["first_name"]
        if students[username]["first_name"] != expected_first_name:
            utils.fail(
                f"Archive for {username}: first_name is {students[username]['first_name']!r}, "
                f"expected {expected_first_name!r} (anonymize={anonymize}).",
            )

        courses = {row["course_id"]: row for row in read_csv(zip_path, "courses.csv")}
        school_class = connection["school_class"]
        pattern = connection["school_settings"].get("course_name_pattern", "{ou}-{name}")
        expected_course_name = pattern.format(
            ou=connection["school"], name=school_class.split("-", 1)[1]
        )
        if courses[school_class]["course_name"] != expected_course_name:
            utils.fail(
                f"Archive for {username}: course_name is {courses[school_class]['course_name']!r}, "
                f"expected {expected_course_name!r}.",
            )


if __name__ == "__main__":
    test = Test()
    test.run()
