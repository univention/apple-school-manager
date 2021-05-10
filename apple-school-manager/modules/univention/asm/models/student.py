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

Class to represent an ASM student.

See https://support.apple.com/en-us/HT207029
"""

from __future__ import absolute_import, unicode_literals
import logging
from .base import AsmModel, AnonymizeMixIn
from ..utils import check_domain, get_default_password_policy, get_person_id, get_ldap_connection, prepend_to_mail_domain
from ucsschool.lib.models.user import Student

try:
	from typing import Any, AnyStr, Iterable, Optional
except ImportError:
	pass


class AsmStudent(AsmModel, AnonymizeMixIn):
	"""Class to represent an ASM student entry."""

	header = (
		'person_id', 'person_number', 'first_name', 'middle_name', 'last_name', 'grade_level',
		'email_address', 'sis_username', 'password_policy', 'location_id'
	)
	ucr_anonymize_key_base = 'asm/attributes/student/anonymize'

	def __init__(
		self,
		person_id,  # type: AnyStr
		first_name,  # type: AnyStr
		last_name,  # type: AnyStr
		location_id,  # type: AnyStr
		person_number=None,  # type: Optional[AnyStr]
		middle_name=None,  # type: Optional[AnyStr]
		grade_level=None,  # type: Optional[AnyStr]
		email_address=None,  # type: Optional[AnyStr]
		sis_username=None,  # type: Optional[AnyStr]
		password_policy=None,  # type: Optional[AnyStr]
		additional_location_ids=None  # type: Optional[Iterable[AnyStr]]
	):
		# type: (...) -> None
		"""
		:param str person_id: The unique identifier for a specific student.
			This `person_id` should match the unique identifier in your SIS if
			available. This `person_id` is the unique identifier for the
			student in Apple School Manager. Use this value to refer to the
			student in the Rosters file and instructors in the Classes file
			(required).
		:param str first_name: The student's first name (required).
		:param str last_name: The student's last name (required).
		:param str location_id: The `location_id` for the student. This must
			correspond with a `location_id` in the Locations file. If this
			entry doesn't match an entry in the Locations file, you will
			experience issues in the upload process (required).
		:param str person_number: Another value that might identify a student
			in your school. This might be a student identification number
			(optional).
		:param str middle_name: The student's middle name (optional).
		:param str grade_level: The student's grade level (optional).
		:param str email_address: An email address for the student (optional).
		:param str sis_username: The user name for the student in your SIS
			(optional).
		:param str password_policy: Use the `password_policy` field to specify
			a password policy for each specific student. This value overrides
			the location password policy and any password policy previously set
			for that student. The `password_policy` field must have the number
			4, 6, 8, or be an emtpy string (`''`). If None, the value of the
			UCR variable asm/attributes/student/password_policy is used
			(optional).
		:param additional_location_ids: list of additional (max 14) locations
			(optional).
		:type location_ids: list(str)
		"""
		if additional_location_ids:
			assert len(additional_location_ids) < 15, 'No more than 14 additional locations are allowed.'
		else:
			additional_location_ids = []
		super(AsmStudent, self).__init__(
			person_id, first_name, last_name, location_id, person_number, middle_name, grade_level,
			email_address, sis_username, additional_location_ids
		)
		self.person_id = person_id
		self.first_name = first_name
		self.last_name = last_name
		self.location_id = location_id
		self.person_number = person_number
		self.middle_name = middle_name
		self.grade_level = grade_level
		self.email_address = email_address
		self.sis_username = sis_username
		self.password_policy = get_default_password_policy() if password_policy is None else password_policy
		self.additional_location_ids = additional_location_ids
		if additional_location_ids:
			# add members, so that default as_csv_line() will work
			location_id_attrs = ['location_id_{}'.format(num) for num in range(2, 2 + len(additional_location_ids))]
			for loc_id_attr, loc_id in zip(location_id_attrs, additional_location_ids):
				setattr(self, loc_id_attr, loc_id)
			# update header
			self.header = list(self.header) + [
				'location_id_{}'.format(num) for num in range(2, 2 + len(additional_location_ids))
			]

	@classmethod
	def from_dn(cls, dn, ou_whitelist=None, *args, **kwargs):
		# type: (str, Optional[Iterable[AnyStr]], *Any, **Any) -> AsmStudent
		"""
		Get AsmStudent object created from data in LDAP object.

		:param str dn: DN to the Student object to represent
		:param ou_whitelist: list of schools/OUs that should be considered when
			looking at ou-overlapping users. No limit if empty or None.
		:type ou_whitelist: list(str) or None
		:return: AsmStudent instance
		:rtype: AsmStudent
		:raises WrongModel: when `dn` does not belong to a student
		:raises ValueError: when non of the users `schools` is in the whitelist
		"""
		lo, po = get_ldap_connection()
		student = Student.from_dn(dn, None, lo)
		if student.email and not check_domain(student.email):
			logger = logging.getLogger(__name__)
			logger.warn('Invalid email domain in %r for DN %r.', student.email, dn)
		email = prepend_to_mail_domain(student.email) if student.email else None
		location_ids = sorted(s for s in student.schools if s != student.school)
		if student.school:
			location_ids = [student.school] + location_ids
		if ou_whitelist:
			location_ids = [l for l in location_ids if l in ou_whitelist]
			if not location_ids:
				raise ValueError('Non of the users schools is in the whitelist: {} (schools: {!r}).'.format(
					student, student.schools))
		additional_attrs = ['middleName', 'initials', 'oxMiddleName']
		additional_attrs.extend({v[1:].strip() for v in cls.anonymize_mapping().values() if v and v.startswith('%')})
		person_id_attr, student_lo = get_person_id(student.dn, 'student', additional_attrs)
		person_id = student_lo[person_id_attr][0]
		middle_name = (
			student_lo.get('middleName', [''])[0] or
			student_lo.get('initials', [''])[0] or
			student_lo.get('oxMiddleName', [''])[0]
		)
		return cls(**cls.anonymize(
			student,
			student_lo,
			person_id=person_id,
			first_name=student.firstname,
			last_name=student.lastname,
			location_id=location_ids[0],
			person_number=person_id,
			middle_name=middle_name,
			grade_level=None,  # TODO: make conf. by UCR which LDAP attr to use
			email_address=email,
			sis_username=student.name,
			password_policy=None,  # UCS password policy doesn't fit and nothing else is ...
			additional_location_ids=location_ids[1:]  # ... stored in LDAP regarding password length
		))
