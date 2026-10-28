# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Class to represent an ASM staff.

See https://support.apple.com/en-us/HT207029
"""

import logging
from collections.abc import Collection, Iterable
from functools import cache
from typing import Any, Self

import univention.asm.api_constraints as asm_api_constraints
from ucsschool.lib.models.base import WrongModel
from ucsschool.lib.models.user import Teacher, TeachersAndStaff
from univention.admin import uexceptions
from univention.admin.uldap import access as LoType  # noqa: N812
from univention.asm.config import Settings
from univention.asm.utils import (
    get_ldap_connection,
    get_person_id,
    prepend_to_mail_domain,
)

from .base import AnonymizeMixIn, AsmModel


class AsmStaff(AsmModel, AnonymizeMixIn):
    """Class to represent an ASM staff entry."""

    header = [
        "person_id",
        "person_number",
        "first_name",
        "middle_name",
        "last_name",
        "email_address",
        "sis_username",
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
        email_address: str | None = None,
        sis_username: str | None = None,
        additional_location_ids: Collection[str] | None = None,
    ) -> None:
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
        self.email_address = email_address
        self.sis_username = sis_username
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
        Get AsmStaff object created from data in LDAP object.

        :param str dn: DN to the Teacher/TeachersAndStaff object to represent
        :param settings: settings of the Apple School Manager account, only
                schools that the account receives are exported. All schools with
                the default settings if None.
        :return: AsmStaff instance
        :rtype: AsmStaff
        :raises WrongModel: when `dn` does not belong to a teacher or
                teacherandstaff
        :raises ValueError: when non of the users `schools` is synchronized to the account
        """
        settings = settings or Settings()
        lo, _po = get_ldap_connection()
        try:
            teacher = Teacher.from_dn(dn, None, lo)
        except WrongModel:
            teacher = TeachersAndStaff.from_dn(dn, None, lo)
        email = (
            prepend_to_mail_domain(teacher.email, settings.email_prepend_domain)
            if teacher.email
            else None
        )
        location_ids = [teacher.school, *sorted(s for s in teacher.schools if s != teacher.school)]
        location_ids = [loc for loc in location_ids if settings.includes(loc)]
        if not location_ids:
            msg = f"Non of the users schools is synchronized to the account: {teacher} (schools: {teacher.schools!r})."
            raise ValueError(msg)
        additional_attrs = ["middleName", "initials", "oxMiddleName"]
        additional_attrs.extend(cls.anonymize_ldap_attributes(settings.staff))
        person_id_attr, teacher_lo = get_person_id(
            teacher.dn,
            settings.staff.person_id_attribute,
            additional_attrs,
        )
        person_id = teacher_lo[person_id_attr][0]
        middle_name = (
            teacher_lo.get("middleName", [""])[0]
            or teacher_lo.get("initials", [""])[0]
            or teacher_lo.get("oxMiddleName", [""])[0]
        )
        return cls(
            **cls.anonymize(
                teacher,
                teacher_lo,
                settings.staff,
                person_id=person_id,
                first_name=teacher.firstname,
                last_name=teacher.lastname,
                location_id=location_ids[0],
                person_number=person_id,
                middle_name=middle_name,
                email_address=email,
                sis_username=teacher.name,
                additional_location_ids=location_ids[1:],
            ),
        )


@cache
def get_filtered_staff(
    lo: LoType,
    logger: logging.Logger,
    school: str,
    specific_ldap_filter: str = "",
) -> Iterable[Teacher]:
    try:
        filtered_teachers: Iterable[Teacher] = Teacher.get_all(
            lo,
            school,
            filter_str=specific_ldap_filter,
        ) + TeachersAndStaff.get_all(
            lo,
            school,
            filter_str=specific_ldap_filter,
        )
    except uexceptions.valueInvalidSyntax:
        logger.exception(f"Invalid LDAP-filter for staff: {specific_ldap_filter!r}")
        raise
    return filtered_teachers
