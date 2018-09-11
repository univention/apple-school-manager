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

Class to represent a OneRoster location.

See https://support.apple.com/en-us/HT207029
"""

from __future__ import absolute_import, unicode_literals
from .base import OneRosterModel
from ucsschool.lib.models import School
from ucsschool.importer.utils.ldap_connection import get_readonly_connection

try:
	from typing import Any, AnyStr
except ImportError:
	pass


class OneRosterLocation(OneRosterModel):
	"""Class to represent a OneRoster location entry."""

	header = ('location_id', 'location_name')

	def __init__(self, location_id, location_name):  # type: (AnyStr, AnyStr) -> None
		"""
		:param str location_id: A unique identifier made of numbers and/or
			letters that contains no spaces (required).
		:param str location_name: The name of the location (required).
		"""
		super(OneRosterLocation, self).__init__(location_id, location_name)
		self.location_id = location_id
		self.location_name = location_name

	@classmethod
	def from_dn(cls, dn, *args, **kwargs):  # type: (AnyStr, *Any, **Any) -> OneRosterLocation
		"""
		Get OneRosterLocation object created from data in LDAP object.

		:param str dn: DN to the School/OU object to represent
		:return: OneRosterLocation instance
		:rtype OneRosterLocation
		"""
		lo, po = get_readonly_connection()
		school = School.from_dn(dn, None, lo)
		return cls(school.name, school.display_name or school.name)
