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

Class to represent an ASM class.

See https://support.apple.com/en-us/HT207029
"""

from __future__ import absolute_import, unicode_literals
import logging

from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.base import UnknownModel


from ..utils import get_ldap_connection, get_person_id, get_ucr
from .base import AsmModel
from .staff import get_filtered_staff

try:
	from typing import Any, AnyStr, Iterable, Optional, Dict, List
except ImportError:
	pass


class AsmClass(AsmModel):
	"""Class to represent an ASM class entry."""

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
		:rtype: AsmClass
		"""
		lo, po = get_ldap_connection()
		ucr = get_ucr()
		logger = logging.getLogger(__name__)
		try:
			school_class = SchoolClass.from_dn(dn, None, lo)
		except UnknownModel:
			school_class = WorkGroup.from_dn(dn, None, lo)
		if cls._class_number_empty is None:
			cls._class_number_empty = ucr.is_true('asm/attributes/classes/class_number_empty', True)
		teachers = []
		expected_teachers = get_filtered_staff(lo, logger, school_class.school)
		expected_teachers_dns = [teacher.dn for teacher in expected_teachers]

		for user_dn in school_class.users:
			if user_dn not in expected_teachers_dns:
				logger.debug("User {} is excluded due to a ldap-filter set in UCR-V asm/ldap_filter/staff".format(user_dn))
				continue
			person_id_attr, teacher_lo = get_person_id(user_dn, 'staff', [])
			teachers.append(teacher_lo[person_id_attr][0])
		instructor_id = instructor_id_2 = instructor_id_3 = additional_instructor_ids = None
		if teachers:
			try:
				instructor_id = teachers[0]
				instructor_id_2 = teachers[1]
				instructor_id_3 = teachers[2]
				additional_instructor_ids = teachers[3:15]
			except IndexError:
				pass
			if len(teachers) > 15:
				logger.warn(
					'Class %r has more than 15 teachers. Only 15 will be synchronized. This is a limitation of the '
					'Apple School Manager service.', school_class.name)
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
