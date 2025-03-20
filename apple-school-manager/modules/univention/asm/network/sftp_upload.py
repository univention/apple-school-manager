#
# Copyright 2018-2020 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

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
