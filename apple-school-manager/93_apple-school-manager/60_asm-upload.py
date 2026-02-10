#!/usr/share/ucs-test/runner python3
## desc: test asm-upload
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47623]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import contextlib
import filecmp
import os
import shutil
import subprocess
from types import TracebackType

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
from paramiko.client import AutoAddPolicy, SSHClient
from ucsschool.lib.models.utils import exec_cmd
from univention.admin.uldap import getMachineConnection
from univention.config_registry import handler_set
from univention.testing import utils
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


class LocalHostAsASM:
    def __init__(self, username: str, password: str, home_dir: str, school_name: str) -> None:
        self.username = username
        self.password = password
        self.school_name = school_name
        subprocess.check_call(["mkhomedir_helper", self.username])
        self.home_dir = home_dir
        self.dropbox = os.path.join(home_dir, "dropbox")

    def __enter__(self) -> None:
        handler_set(
            [
                "hosts/static/127.0.60.60=upload.appleschoolcontent.com",
                f"asm/username={self.username}",
                "asm/store_zip=yes",
                f"asm/school_whitelist={self.school_name}",
                f"auth/sshd/user/{self.username}=yes",
            ],
        )
        os.rename("/etc/asm_public_key", "/etc/asm_public_key.backup_60test")
        if os.path.exists("/etc/asm.secret"):
            os.rename("/etc/asm.secret", "/etc/asm.secret.backup_60test")
        with open("/etc/asm.secret", "w") as asm_secret_file:
            asm_secret_file.write(self.password)
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())  # noqa: S507
        client.connect("upload.appleschoolcontent.com", username=self.username, password=self.password)
        sftp = client.open_sftp()
        sftp.chdir(self.home_dir)
        sftp.mkdir("dropbox")
        client.save_host_keys("/etc/asm_public_key")
        client.close()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        os.rename("/etc/asm_public_key.backup_60test", "/etc/asm_public_key")
        if os.path.exists("/etc/asm.secret.backup_60test"):
            os.rename("/etc/asm.secret.backup_60test", "/etc/asm.secret")
        with contextlib.suppress(OSError):
            shutil.rmtree(self.dropbox)


class TempUserWritableFileAnywhere:
    def __init__(self, path: str, uid: int, gid: int) -> None:
        self.path = path
        self.uid = uid
        self.gid = gid

    def __enter__(self) -> None:
        with open(self.path, "w") as fp:
            print(f"Creating file {self.path!r} with uid={self.uid!r} and gid={self.gid!r}...")
            os.fchown(fp.fileno(), self.uid, self.gid)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        with contextlib.suppress(OSError):
            print(f"Deleting file {self.path!r}...")
            os.unlink(self.path)


class Test(ImportTestbase):  # type: ignore[misc]
    ou_B = None
    ou_C = None

    def test(self) -> None:
        school_class = f"{self.ou_A.name}-{uts.random_username()}"
        student1_name, student1_dn = self.schoolenv.create_student(
            self.ou_A.name,
            classes=school_class,
            password="univention",
        )
        lo, _po = getMachineConnection()
        user_attrs = lo.get(student1_dn, attr=["homeDirectory", "uidNumber", "gidNumber"])
        home_dir = user_attrs["homeDirectory"][0].decode()
        uid = int(user_attrs["uidNumber"][0])
        gid = int(user_attrs["gidNumber"][0])
        remote_path = "/archive.zip"
        with (
            ucr_test.UCSTestConfigRegistry(),
            LocalHostAsASM(
                student1_name,
                "univention",
                home_dir,
                self.ou_A.name,
            ),
            TempUserWritableFileAnywhere(remote_path, uid, gid),
        ):
            cmd = ["/usr/sbin/asm-upload"]
            print(f"Executing {cmd!r}...")
            returncode, stdout, stderr = exec_cmd(cmd)
            print(f"-> returncode={returncode}")
            print(f"-> stdout={stdout}")
            print(f"-> stderr={stderr}")
            if returncode:
                utils.fail(f"{cmd!r} returned {returncode}.)")
            for line in stderr.split("\n"):
                if line.startswith("The uploaded zip is stored in: "):
                    zip_path = line.split()[-1]
                    print(f"Comparing zip_path={zip_path!r} and remote_path={remote_path!r}...")
                    if not filecmp.cmp(zip_path, remote_path, shallow=False):
                        utils.fail("ZIP file was not correctly uploaded")
                    return
            utils.fail("Something with the upload seems to be broken.")


if __name__ == "__main__":
    test = Test()
    test.run()
