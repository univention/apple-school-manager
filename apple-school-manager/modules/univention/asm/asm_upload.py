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

export school data to asm
"""

import logging
import os
from datetime import datetime

from univention.config_registry import handler_set

from .csv.zip_file import AsmZipFile
from .network.sftp_upload import SFTP, MissingPublicSshKeyError

ASM_PUBLIC_KEY = "/etc/asm_public_key"


class ASMUpload:
    def __init__(
        self,
        username: str,
        password: str,
        ou_whitelist: list[str] | None = None,
        delete_zip_file: bool = True,  # noqa: FBT001
    ) -> None:
        try:
            with open(ASM_PUBLIC_KEY) as asm_public_key_file:
                self.host_key_line = asm_public_key_file.read()
        except FileNotFoundError:
            err_msg = f"Could not find {ASM_PUBLIC_KEY}"
            raise MissingPublicSshKeyError(err_msg)
        self.hostname = "upload.appleschoolcontent.com"
        self.username = username
        self.password = password
        self.ou_whitelist = ou_whitelist
        self.delete_zip_file = delete_zip_file
        self.logger = logging.getLogger(__name__)

    def upload(self, folder_path: str = "/var/lib/asm") -> str | None:
        file_path = os.path.join(folder_path, f"asm_{datetime.isoformat(datetime.now())}.zip")
        zip_path = AsmZipFile(file_path, self.ou_whitelist).write_zip()
        self.logger.info("Uploading ZIP file to %s...", self.hostname)
        with SFTP(self.hostname, self.username, self.password, self.host_key_line) as sftp:
            self.logger.debug("Connected to %s.", self.hostname)
            sftp.upload(zip_path)
            self.logger.info("Finished uploading ZIP file.")

        self.logger.debug("Disconnected.")
        handler_set([f"asm/last_upload={datetime.isoformat(datetime.now())}"])
        if self.delete_zip_file:
            os.remove(zip_path)
            self.logger.debug("Deleted ZIP file.")
            return None
        return zip_path
