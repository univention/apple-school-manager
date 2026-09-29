# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Class to represent an ASM student.

See https://support.apple.com/en-us/HT207029
"""

import logging
from collections.abc import Collection
from typing import Any, Self

from ucsschool.lib.models.user import Student

import univention.asm.api_constraints as asm_api_constraints
from univention.asm.config import Settings, StudentSettings
from univention.asm.utils import (
    check_domain,
    get_ldap_connection,
    get_person_id,
    prepend_to_mail_domain,
)

from .base import AnonymizeMixIn, AsmModel


class AsmStudent(AsmModel, AnonymizeMixIn):
    """Class to represent an ASM student entry."""

    header = [
        "person_id",
        "person_number",
        "first_name",
        "middle_name",
        "last_name",
        "grade_level",
        "email_address",
        "sis_username",
        "password_policy",
        "location_id",
    ]

    def __init__(
        self,
        person_id: str,
        first_name: str,
        last_name: str,
        location_id: str,
        person_number: str | None = None,
        middle_name: str | None = None,
        grade_level: str | None = None,
        email_address: str | None = None,
        sis_username: str | None = None,
        password_policy: str | None = None,
        additional_location_ids: Collection[str] | None = None,
    ) -> None:
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
                4, 6, 8, or be an emtpy string (`''`). If None, the default of
                the setting ``password_policy`` is used (optional).
        :param additional_location_ids: list of additional (max 14) locations
                (optional).
        :type location_ids: list(str)
        """
        if additional_location_ids:
            asm_api_constraints.validate_additional_location_limit(additional_location_ids)
        else:
            additional_location_ids = []
        super().__init__(
            person_id,
            first_name,
            last_name,
            location_id,
            person_number,
            middle_name,
            grade_level,
            email_address,
            sis_username,
            additional_location_ids,
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
        self.password_policy = (
            password_policy_value(StudentSettings()) if password_policy is None else password_policy
        )
        self.additional_location_ids = additional_location_ids
        if additional_location_ids:
            # add members, so that default as_csv_line() will work
            location_id_attrs = [
                f"location_id_{num}" for num in range(2, 2 + len(additional_location_ids))
            ]
            for loc_id_attr, loc_id in zip(location_id_attrs, additional_location_ids, strict=False):
                setattr(self, loc_id_attr, loc_id)
            # update header
            self.header = self.header + [
                f"location_id_{num}" for num in range(2, 2 + len(additional_location_ids))
            ]

    @classmethod
    def from_dn(cls, dn: str, settings: Settings | None = None, *args: Any, **kwargs: Any) -> Self:
        """
        Get AsmStudent object created from data in LDAP object.

        :param str dn: DN to the Student object to represent
        :param settings: settings of the Apple School Manager account, only
                schools that the account receives are exported. All schools with
                the default settings if None.
        :return: AsmStudent instance
        :rtype: AsmStudent
        :raises WrongModel: when `dn` does not belong to a student
        :raises ValueError: when non of the users `schools` is synchronized to the account
        """
        settings = settings or Settings()
        lo, _po = get_ldap_connection()
        student = Student.from_dn(dn, None, lo)
        if student.email and not check_domain(student.email):
            logger = logging.getLogger(__name__)
            logger.warning("Invalid email domain in %r for DN %r.", student.email, dn)
        email = (
            prepend_to_mail_domain(student.email, settings.email_prepend_domain)
            if student.email
            else None
        )
        location_ids = sorted(s for s in student.schools if s != student.school)
        if student.school:
            location_ids = [student.school, *location_ids]
        location_ids = [loc for loc in location_ids if settings.includes(loc)]
        if not location_ids:
            msg = f"Non of the users schools is synchronized to the account: {student} (schools: {student.schools!r})."
            raise ValueError(msg)
        additional_attrs = ["middleName", "initials", "oxMiddleName"]
        grade_level_attribute = settings.student.grade_level_attribute
        if grade_level_attribute:
            additional_attrs.append(grade_level_attribute)
        additional_attrs.extend(cls.anonymize_ldap_attributes(settings.student))
        person_id_attr, student_lo = get_person_id(
            student.dn,
            settings.student.person_id_attribute,
            additional_attrs,
        )
        person_id = student_lo[person_id_attr][0]
        middle_name = (
            student_lo.get("middleName", [""])[0]
            or student_lo.get("initials", [""])[0]
            or student_lo.get("oxMiddleName", [""])[0]
        )
        grade_level = student_lo.get(grade_level_attribute, [None])[0] if grade_level_attribute else None
        return cls(
            **cls.anonymize(
                student,
                student_lo,
                settings.student,
                person_id=person_id,
                first_name=student.firstname,
                last_name=student.lastname,
                location_id=location_ids[0],
                person_number=person_id,
                middle_name=middle_name,
                grade_level=grade_level,
                email_address=email,
                sis_username=student.name,
                password_policy=password_policy_value(settings.student),
                additional_location_ids=location_ids[1:],
            ),
        )


def password_policy_value(settings: StudentSettings) -> str:
    """Return the ``password_policy`` column for the setting ``password_policy``."""
    return "" if settings.password_policy is None else str(settings.password_policy)
