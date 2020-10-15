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

Class to represent an ASM staff.

See https://support.apple.com/en-us/HT207029
"""

from __future__ import absolute_import, unicode_literals
import logging
from .base import AsmModel, AnonymizeMixIn
from ..utils import check_domain, get_ldap_connection, get_person_id, prepend_to_mail_domain
from ucsschool.lib.models import Teacher, TeachersAndStaff
from ucsschool.lib.models.base import WrongModel

try:
	from typing import Any, AnyStr, Iterable, Optional
except ImportError:
	pass


class AsmStaff(AsmModel, AnonymizeMixIn):
	"""Class to represent an ASM staff entry."""

	header = (
		'person_id', 'person_number', 'first_name', 'middle_name', 'last_name', 'email_address', 'sis_username',
		'location_id'
	)
	ucr_anonymize_key_base = 'asm/attributes/staff/anonymize'

	def __init__(
			self,
			person_id,  # type: AnyStr
			first_name,  # type: AnyStr
			last_name,  # type: AnyStr
			location_id,  # type: AnyStr
			person_number=None,  # type: Optional[AnyStr]
			middle_name=None,  # type: Optional[AnyStr]
			email_address=None,  # type: Optional[AnyStr]
			sis_username=None,  # type: Optional[AnyStr]
			additional_location_ids=None  # type: Optional[Iterable[AnyStr]]
	):
		# type: (...) -> None
		"""
		:param str person_id: The unique identifier for a specific staff
			member. This person_id should match the unique identifier in your
			SIS if available. This person_id is the unique identifier for the
			staff member in Apple School Manager. Use this value to refer to
			instructors in the Classes file (required).
		:param str first_name: The staff member's first name (required).
		:param str last_name: The staff member's last name (required).
		:param str location_id: The location_id for the staff member. This
			should correspond with a location_id in the Locations file. If this
			entry doesn't match an entry in the Locations file, you will
			experience issues in the upload process (required).
		:param str person_number: Another value that might identify a staff
			member in your school. This might be a staff badge number
			(optional).
		:param str middle_name: The staff member's middle name (optional).
		:param str email_address: An email address for this staff member
			(optional).
		:param str sis_username: The user name for the staff member in your
			SIS (optional).
		:param additional_location_ids: list of additional (max 14) locations
			(optional).
		"""
		if additional_location_ids:
			assert len(additional_location_ids) < 15, 'No more than 14 additional locations are allowed.'
		else:
			additional_location_ids = []
		super(AsmStaff, self).__init__(
			person_id, first_name, last_name, location_id, person_number, middle_name, email_address, sis_username,
			additional_location_ids
		)
		self.person_id = person_id
		self.first_name = first_name
		self.last_name = last_name
		self.location_id = location_id
		self.person_number = person_number
		self.middle_name = middle_name
		self.email_address = email_address
		self.sis_username = sis_username
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
		# type: (AnyStr, Optional[Iterable[AnyStr]], *Any, **Any) -> AsmStaff
		"""
		Get AsmStaff object created from data in LDAP object.

		:param str dn: DN to the Teacher/TeachersAndStaff object to represent
		:param ou_whitelist: list of schools/OUs that should be considered when
			looking at ou-overlapping users. No limit if empty or None.
		:type ou_whitelist: list(str) or None
		:return: AsmStaff instance
		:rtype: AsmStaff
		:raises WrongModel: when `dn` does not belong to a teacher or
			teacherandstaff
		:raises ValueError: when non of the users `schools` is in the whitelist
		"""
		lo, po = get_ldap_connection()
		try:
			teacher = Teacher.from_dn(dn, None, lo)
		except WrongModel:
			teacher = TeachersAndStaff.from_dn(dn, None, lo)
		if teacher.email and not check_domain(teacher.email):
			logger = logging.getLogger(__name__)
			logger.warn('Invalid email domain in %r for DN %r.', teacher.email, dn)
		email = prepend_to_mail_domain(teacher.email) if teacher.email else None
		location_ids = [teacher.school] + sorted(s for s in teacher.schools if s != teacher.school)
		if ou_whitelist:
			location_ids = [l for l in location_ids if l in ou_whitelist]
			if not location_ids:
				raise ValueError('Non of the users schools is in the whitelist: {} (schools: {!r}).'.format(
					teacher, teacher.schools))
		additional_attrs = ['middleName', 'initials', 'oxMiddleName']
		additional_attrs.extend({v[1:].strip() for v in cls.anonymize_mapping().values() if v and v.startswith('%')})
		person_id_attr, teacher_lo = get_person_id(teacher.dn, 'staff', additional_attrs)
		person_id = teacher_lo[person_id_attr][0]
		middle_name = (
				teacher_lo.get('middleName', [''])[0] or
				teacher_lo.get('initials', [''])[0] or
				teacher_lo.get('oxMiddleName', [''])[0]
		)
		return cls(**cls.anonymize(
			teacher,
			teacher_lo,
			person_id=person_id,
			first_name=teacher.firstname,
			last_name=teacher.lastname,
			location_id=location_ids[0],
			person_number=person_id,
			middle_name=middle_name,
			email_address=email,
			sis_username=teacher.name,
			additional_location_ids=location_ids[1:]
		))
