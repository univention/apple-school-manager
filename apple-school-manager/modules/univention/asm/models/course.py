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

Class to represent an ASM course.

See https://support.apple.com/en-us/HT207029
"""

from __future__ import absolute_import, unicode_literals
from .base import AsmModel
from ..utils import get_ldap_connection
from ucsschool.lib.models import SchoolClass, WorkGroup
from ucsschool.lib.models.base import UnknownModel

try:
	from typing import Any, AnyStr, Optional
except ImportError:
	pass


class AsmCourse(AsmModel):
	"""Class to represent an ASM course entry."""

	header = ('course_id', 'course_number', 'course_name', 'location_id')

	def __init__(
			self,
			course_id,  # type: AnyStr
			location_id,  # type: AnyStr
			course_number=None,  # type: Optional[AnyStr]
			course_name=None,  # type: Optional[AnyStr]
	):
		# type: (...) -> None
		"""
		:param str course_id: A unique identifier for the course. This must
			match the corresponding `course_id` used in the Classes file
			(required).
		:param str location_id: The `location_id` for the course. This should
			correspond with a `location_id` in the Locations file. If this
			entry doesn't match an entry in the Locations file, you will
			experience issues in the upload process (required).
		:param str course_number: A number for the course. This number might
			be the course number in your SIS or your curriculum guide
			(optional).
		:param str course_name: The name of your course (optional).
		"""
		super(AsmCourse, self).__init__(course_id, location_id, course_number, course_name)
		self.course_id = course_id
		self.location_id = location_id
		self.course_number = course_number
		self.course_name = course_name

	@classmethod
	def from_dn(cls, dn, *args, **kwargs):  # type: (AnyStr, *Any, **Any) -> AsmCourse
		"""
		Get AsmCourse object created from data in LDAP object.

		:param str dn: DN to the SchoolClass/Workgroup object to represent
		:return: AsmCourse instance
		:rtype AsmCourse
		"""
		lo, po = get_ldap_connection()
		try:
			school_class = SchoolClass.from_dn(dn, None, lo)
		except UnknownModel:
			school_class = WorkGroup.from_dn(dn, None, lo)
		return cls(
			course_id=school_class.name,
			location_id=school_class.school,
			course_number=school_class.name,
			course_name=school_class.description or school_class.name,
		)
