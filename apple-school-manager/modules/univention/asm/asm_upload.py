# -*- coding: utf-8 -*-
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
Univention Apple School Manager Connector

export school data to asm
"""

from __future__ import absolute_import
import os
import logging
from datetime import datetime

from .csv.zip_file import AsmZipFile
from .network.sftp_upload import SFTP
from univention.config_registry import handler_set


class ASMUpload(object):

	def __init__(self, username, password, ou_whitelist=None, delete_zip_file=True):
		with open("/etc/asm_public_key", "r") as asm_public_key_file:
			self.host_key_line = asm_public_key_file.read()
		self.hostname = "upload.appleschoolcontent.com"
		self.username = username
		self.password = password
		self.ou_whitelist = ou_whitelist
		self.delete_zip_file = delete_zip_file
		self.logger = logging.getLogger(__name__)

	def upload(self, folder_path="/var/lib/asm"):
		file_path = os.path.join(folder_path, "asm_{}.zip".format(datetime.isoformat(datetime.now())))
		zip_path = AsmZipFile(file_path, self.ou_whitelist).write_zip()
		self.logger.info('Uploading ZIP file to %s...', self.hostname)
		with SFTP(self.hostname, self.username, self.password, self.host_key_line) as sftp:
			self.logger.debug('Connected to %s.', self.hostname)
			sftp.upload(zip_path)
			self.logger.info('Finished uploading ZIP file.')

		self.logger.debug('Disconnected.')
		handler_set(["asm/last_upload={}".format(datetime.isoformat(datetime.now()))])
		if self.delete_zip_file:
			os.remove(zip_path)
			self.logger.debug('Deleted ZIP file.')
		else:
			return zip_path
