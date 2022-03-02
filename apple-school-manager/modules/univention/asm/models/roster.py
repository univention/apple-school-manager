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

Class to represent an ASM roster.

See https://support.apple.com/en-us/HT207029
"""


from .base import AsmModel
from ..utils import get_person_id, get_ldap_connection
from ucsschool.lib.models.base import UnknownModel
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.user import Student

try:
	from typing import Any, AnyStr
except ImportError:
	pass


class AsmRoster(AsmModel):
	"""Class to represent an ASM roster entry."""

	header = ('roster_id', 'class_id', 'student_id')

	def __init__(
			self,
			roster_id,  # type: AnyStr
			class_id,  # type: AnyStr
			student_id,  # type: AnyStr
	):
		# type: (...) -> None
		"""
		:param str roster_id: A unique identifier for the roster in your SIS
			or other course database (if available) (required).
		:param str class_id: A unique alphanumeric identifier for the class.
			This must match a class_id in the Class file (required).
		:param str student_id: A person_id for one student (required).
		"""
		super(AsmRoster, self).__init__(roster_id, class_id, student_id)
		self.roster_id = roster_id
		self.class_id = class_id
		self.student_id = student_id

	@classmethod
	def from_dn(cls, class_dn, student_dn, *args, **kwargs):  # type: (AnyStr, AnyStr, *Any, **Any) -> AsmRoster
		"""
		Get AsmRoster object created from data in LDAP object.

		:param str class_dn: DN to the SchoolClass/Workgroup object to represent
		:param str student_dn: DN to the student object to represent
		:return: AsmRoster instance
		:rtype: AsmRoster
		"""
		lo, po = get_ldap_connection()
		try:
			school_class = SchoolClass.from_dn(class_dn, None, lo)
		except UnknownModel:
			school_class = WorkGroup.from_dn(class_dn, None, lo)
		student = Student.from_dn(student_dn, None, lo)
		person_id_attr, student_lo = get_person_id(student.dn, 'student', [])
		person_id = student_lo[person_id_attr][0]
		return cls(
			roster_id='{}-{}'.format(school_class.name, person_id),
			class_id=school_class.name,
			student_id=person_id,
		)
