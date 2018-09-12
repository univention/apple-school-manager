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

Classes the produce OneRoster ZIP files containing CSV files.

See https://support.apple.com/en-us/HT207029
"""

from __future__ import absolute_import, unicode_literals
import os
import logging
import tempfile
import zipfile
from univention.oneroster.csv.csv_file import create_csv_files

try:
	from typing import AnyStr, Iterable, List, Optional
except ImportError:
	pass


class OneRosterZipFile(object):
	"""Class to create a ZIP file with OneRoster CSV files."""

	def __init__(self, file_path, ou_whitelist=None):  # type: (AnyStr, Optional[Iterable[AnyStr]]) -> None
		"""
		:param str file_path: file path to write ZIP to
		:param ou_whitelist: list of schools/OUs that should be considered when looking for LDAP objects. No limit if empty or None.
		:type ou_whitelist: list(str) or None
		"""
		self.file_path = file_path
		self.ou_whitelist = ou_whitelist
		self.csv_files = []
		self.logger = logging.getLogger(__name__)

	def create_csv_files(self):  # type: () -> List[AnyStr]
		"""
		Create OneRoster CSV files.

		File names will be saved to :py:attr:`self.file_path`.

		:return: list of files created
		:rtype: list(str)
		"""
		tmp_dir = tempfile.mkdtemp()
		self.logger.debug('Creating CSV files in %s...', tmp_dir)
		self.csv_files = create_csv_files(tmp_dir, self.ou_whitelist)
		assert self.csv_files, 'No CSV files were created.'
		self.logger.debug('Created CSV files: %s.', ', '.join(sorted(self.csv_files)))
		return self.csv_files

	def write_zip(self, file_path=None, delete_csv_files=True):  # type: (Optional[AnyStr], Optional[bool]) -> AnyStr
		"""
		Compress CSV files into a ZIP file. An existing file will be overwritten.

		If :py:attr:`self.csv_files` is non-empty, those files will be used,
		else they will be created.

		:param str file_path: path to write ZIP to, if unset will be written to :py:attr:`self.file_path`
		:param bool delete_csv_files: whether the CSV files should be removed afterwards
		:return: path to the created ZIP file
		:rtype: str
		"""
		file_path = file_path or self.file_path
		assert file_path, 'ZIP file path is empty.'
		self.logger.info('Creating ZIP file in %s...', file_path)
		if self.csv_files:
			self.logger.debug('Using existing CSV files: %s.', ', '.join(sorted(self.csv_files)))
		else:
			self.csv_files = self.create_csv_files()
		self.logger.debug('Writing ZIP file to %s...', file_path)
		with open(file_path,  'wb') as fp, zipfile.ZipFile(fp, 'w', zipfile.ZIP_DEFLATED) as zf:
			os.fchmod(fp.fileno(), 0o600)
			for path in sorted(self.csv_files):
				zf.write(path, os.path.basename(path))
		self.logger.debug('Done writing ZIP file.')
		if delete_csv_files:
			self.logger.debug('Deleting temporary CSV files and directory...')
			for path in self.csv_files:
				os.remove(path)
			os.rmdir(os.path.dirname(self.csv_files[0]))
		self.logger.info('Finished creating ZIP file.')
		return file_path
