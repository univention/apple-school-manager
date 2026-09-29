# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Class to represent an ASM class.

See https://support.apple.com/en-us/HT207029
"""

import logging
from collections.abc import Collection
from typing import Any, Self

from ucsschool.lib.models.base import UnknownModel
from ucsschool.lib.models.group import SchoolClass, WorkGroup

import univention.asm.api_constraints as asm_api_constraints
from univention.asm.config import Settings
from univention.asm.utils import get_ldap_connection, get_person_id

from .base import AsmModel
from .staff import get_filtered_staff


class AsmClass(AsmModel):
    """Class to represent an ASM class entry."""

    header = [
        "class_id",
        "class_number",
        "course_id",
        "instructor_id",
        "instructor_id_2",
        "instructor_id_3",
        "location_id",
    ]

    def __init__(
        self,
        class_id: str,
        course_id: str,
        location_id: str,
        class_number: str | None = None,
        instructor_id: str | None = None,
        instructor_id_2: str | None = None,
        instructor_id_3: str | None = None,
        additional_instructor_ids: Collection[str] | None = None,
    ) -> None:
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
            asm_api_constraints.validate_additional_instructor_limit(additional_instructor_ids)
        else:
            additional_instructor_ids = []
        super().__init__(
            class_id,
            course_id,
            location_id,
            class_number,
            instructor_id,
            instructor_id_2,
            instructor_id_3,
            additional_instructor_ids,
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
            instructor_id_attrs = [
                f"instructor_id_{num}" for num in range(4, 4 + len(additional_instructor_ids))
            ]
            for instr_id_attr, instr_id in zip(
                instructor_id_attrs, additional_instructor_ids, strict=False
            ):
                setattr(self, instr_id_attr, instr_id)
            # update header
            self.header = self.header + [
                f"instructor_id_{num}" for num in range(4, 4 + len(additional_instructor_ids))
            ]

    @classmethod
    def from_dn(cls, dn: str, settings: Settings | None = None, *args: Any, **kwargs: Any) -> Self:
        """
        Get AsmClass object created from data in LDAP object.

        :param str dn: DN to the SchoolClass/Workgroup object to represent
        :param settings: settings of the Apple School Manager account, the
                default settings if None
        :return: AsmClass instance
        :rtype: AsmClass
        """
        settings = settings or Settings()
        lo, _po = get_ldap_connection()
        logger = logging.getLogger(__name__)
        try:
            school_class = SchoolClass.from_dn(dn, None, lo)
        except UnknownModel:
            school_class = WorkGroup.from_dn(dn, None, lo)
        school_settings = settings.school(school_class.school)
        teachers = []
        expected_teachers = get_filtered_staff(
            lo,
            logger,
            school_class.school,
            school_settings.staff_ldap_filter,
        )
        expected_teachers_dns = [teacher.dn for teacher in expected_teachers]

        for user_dn in school_class.users:
            if user_dn not in expected_teachers_dns:
                logger.debug(
                    f"User {user_dn} is excluded due to the staff ldap_filter of {school_class.school}",
                )
                continue
            person_id_attr, teacher_lo = get_person_id(user_dn, settings.staff.person_id_attribute, [])
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
                logger.warning(
                    "Class %r has more than 15 teachers. Only 15 will be synchronized. This is a limitation of the "
                    "Apple School Manager service.",
                    school_class.name,
                )
        return cls(
            class_id=school_class.name,
            course_id=school_class.name,
            location_id=school_class.school,
            class_number="" if school_settings.class_number_empty else school_class.name,
            instructor_id=instructor_id,
            instructor_id_2=instructor_id_2,
            instructor_id_3=instructor_id_3,
            additional_instructor_ids=additional_instructor_ids,
        )
