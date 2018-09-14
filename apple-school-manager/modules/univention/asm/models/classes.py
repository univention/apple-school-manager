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

Class to represent a ASM class.

See https://support.apple.com/en-us/HT207029
"""

from __future__ import absolute_import, unicode_literals
from .base import AsmModel
from ucsschool.lib.models import SchoolClass, User, WorkGroup
from ucsschool.lib.models.base import UnknownModel
from univention.asm.utils import get_ucr
from ucsschool.importer.utils.ldap_connection import get_readonly_connection

try:
	from typing import Any, AnyStr, Iterable, Optional
except ImportError:
	pass


class AsmClass(AsmModel):
	"""Class to represent a ASM class entry."""

	header = (
		'class_id', 'class_number', 'course_id', 'instructor_id', 'instructor_id_2', 'instructor_id_3',
		'location_id'
	)
	_class_number_empty = None

	def __init__(
			self,
			class_id,  # type: AnyStr
			course_id,  # type: AnyStr
			location_id,  # type: AnyStr
			class_number=None,  # type: Optional[AnyStr]
			instructor_id=None,  # type: Optional[AnyStr]
			instructor_id_2=None,  # type: Optional[AnyStr]
			instructor_id_3=None,  # type: Optional[AnyStr]
			additional_instructor_ids=None  # type: Optional[Iterable[AnyStr]]
	):
		# type: (...) -> None
		"""
		:param str class_id: A unique identifier for the class (required).
		:param str course_id: The `course_id` of the course this class belongs
			to. This must match a course_id in the Courses file (required).
		:param str location_id: The `location_id` for the class. This should
			correspond with the location_id in the Locations file. If this
			entry doesn't match an entry in the Locations file, you will
			experience issues in the upload process (required).
		:param str class_number: A number or code that identifies this class in
			your institution. Unlike class_id, class_number isn't used to refer
			to this class in CSV rosters (optional).
		:param str instructor_id: The person_id for the instructor. This must
			match the person_id used in the Staff file (optional).
		:param str instructor_id_2: The person_id for the instructor. This must
			match the person_id used in the Staff file (optional).
		:param str instructor_id_3: The person_id for the instructor. This must
			match the person_id used in the Staff file (optional).
		:param additional_instructor_ids: list of additional (max. 12)
			instructors (optional).
		:type additional_instructor_ids: list(str)
		"""
		if additional_instructor_ids:
			assert len(additional_instructor_ids) < 13, 'No more than 12 additional instructors are allowed.'
		else:
			additional_instructor_ids = []
		super(AsmClass, self).__init__(
			class_id, course_id, location_id, class_number, instructor_id, instructor_id_2,
			instructor_id_3, additional_instructor_ids
		)
		self.class_id = class_id
		self.course_id = course_id
		self.location_id = location_id
		self.class_number = class_number
		self.instructor_id = instructor_id
		self.instructor_id_2 = instructor_id_2
		self.instructor_id_3 = instructor_id_3
		self.additional_instructor_ids = additional_instructor_ids
		if additional_instructor_ids:
			# add members, so that default as_csv_line() will work
			instructor_id_attrs = ['instructor_id_{}'.format(num) for num in range(4, 4 + len(additional_instructor_ids))]
			for instr_id_attr, instr_id in zip(instructor_id_attrs, additional_instructor_ids):
				setattr(self, instr_id_attr, instr_id)
			# update header
			self.header = list(self.header) + [
				'instructor_id_{}'.format(num) for num in range(4, 4 + len(additional_instructor_ids))
			]

	@classmethod
	def from_dn(cls, dn, *args, **kwargs):  # type: (AnyStr, *Any, **Any) -> AsmClass
		"""
		Get AsmClass object created from data in LDAP object.

		:param str dn: DN to the SchoolClass/Workgroup object to represent
		:return: AsmClass instance
		:rtype AsmClass
		"""
		lo, po = get_readonly_connection()
		try:
			school_class = SchoolClass.from_dn(dn, None, lo)
		except UnknownModel:
			school_class = WorkGroup.from_dn(dn, None, lo)
		if cls._class_number_empty is None:
			cls._class_number_empty = get_ucr().is_true('asm/attributes/classes/class_number_empty', True)
		teachers = []
		for user_dn in school_class.users:
			user = User.from_dn(user_dn, None, lo)
			if user.is_teacher(lo):
				teachers.append(user.name)
		instructor_id = instructor_id_2 = instructor_id_3 = additional_instructor_ids = None
		if teachers:
			try:
				instructor_id = teachers[0]
				instructor_id_2 = teachers[1]
				instructor_id_3 = teachers[2]
				additional_instructor_ids = teachers[3:]
			except IndexError:
				pass
		return cls(
			class_id=school_class.name,
			course_id=school_class.name,
			location_id=school_class.school,
			class_number='' if cls._class_number_empty else school_class.name,
			instructor_id=instructor_id,
			instructor_id_2=instructor_id_2,
			instructor_id_3=instructor_id_3,
			additional_instructor_ids=additional_instructor_ids
		)
