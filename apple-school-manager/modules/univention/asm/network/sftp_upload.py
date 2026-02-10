# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

sftp upload
"""

import os
from types import TracebackType
from typing import Self

import paramiko


class MissingPublicSshKeyError(Exception):
    pass


class SFTP:
    def __init__(self, hostname: str, username: str, password: str, host_key_line: str) -> None:
        self.client = paramiko.client.SSHClient()
        self._set_host_key(host_key_line)
        self.client.connect(hostname, username=username, password=password)
        self.sftpClient = self.client.open_sftp()

    def __enter__(self) -> Self:
        self.client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.client.__exit__(exc_type, exc_value, traceback)

    def _set_host_key(self, host_key_line: str) -> None:
        hostKeyEntry = paramiko.hostkeys.HostKeyEntry.from_line(host_key_line)
        if hostKeyEntry is None:
            err_msg = "Could not load apple public ssh key"
            raise MissingPublicSshKeyError(err_msg)
        host_keys = self.client.get_host_keys()
        for hostname in hostKeyEntry.hostnames:
            host_keys.add(hostname, hostKeyEntry.key.get_name(), hostKeyEntry.key)

    def upload(self, filename: str, remote_folder: str = "/") -> None:
        remote_filename = os.path.join(remote_folder, "archive.zip")
        self.sftpClient.put(filename, remote_filename, confirm=False)  # bug #54553
