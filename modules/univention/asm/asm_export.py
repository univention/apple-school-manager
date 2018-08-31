# -*- coding: utf-8 -*-
#
# Copyright 2018 Univention GmbH
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
Univention Apple School Manager Connector

export school data to asm
"""

import tempfile

from univention.config_registry import ConfigRegistry
from univention.oneroster.csv.zip_file import OneRosterZipFile
from univention.oneroster.network.sftp_upload import SFTP


class ASMExport(object):

	def __init__(self, username=None, password=None, ou_whitelist=None):
		ucr = ConfigRegistry()
		ucr.load()
		ucr_username_key = "asm/username"
		ucr_password_key = "asm/password"
		ucr_ou_whitelist_key = "asm/ou_whitelist"
		self.host_key_line = (
			"upload.appleschoolcontent.com ssh-rsa "
			"AAAAB3NzaC1yc2EAAAADAQABAAABAQCsvd7K2o4VQt5dKxpQMifW0M8s"
			"KExqyjvjh4tp8EhG2tCsENA8iXvJ66CI8NINx4REUkrzCLbE/c2GAKVQ"
			"ATmV5dZX8aCsIyciaXBm6gIU9ttVnH088ZoboQGVLOZvfBE+pQwFjvpH"
			"2LGuUZ+oO34qNBYM9bRaW7os17joe5EHRJaVgQkr7mTli1X/JRwh/tHy"
			"D6D7a+cB/+LMgOh0bp+muFASnrD95YVmHJ6SoafDFfa2UlnpZR2J0irI"
			"S3bLvzqOsxs8f2R/6BObGBHQwQrUysdBCTZBUVDn5flEKzoE3WDTmzEG"
			"IzIl4hIbcuWrLCffO9fMDxbIai86LNqOAH15"
		)
		self.hostname = "upload.appleschoolcontent.com"
		self.username = username or ucr[ucr_username_key]
		self.password = password or ucr[ucr_password_key]
		self.ou_whitelist = ou_whitelist or ucr[ucr_ou_whitelist_key]

	def upload(self):
		with tempfile.NamedTemporaryFile(suffix=".zip") as zip_result_file:
			zip_path = OneRosterZipFile(zip_result_file.name, self.ou_whitelist).write_zip()
			with SFTP(self.hostname, self.username, self.password, self.host_key_line) as sftp:
				sftp.upload(zip_path)
