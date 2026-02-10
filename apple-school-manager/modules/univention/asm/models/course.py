# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Class to represent an ASM course.

See https://support.apple.com/en-us/HT207029
"""

import logging
from typing import Any, Self

from ucsschool.lib.models.base import UnknownModel
from ucsschool.lib.models.group import SchoolClass, WorkGroup

from univention.asm.utils import get_ldap_connection, get_ucr

from .base import AsmModel


class AsmCourse(AsmModel):
    """Class to represent an ASM course entry."""

    header = ["course_id", "course_number", "course_name", "location_id"]

    def __init__(
        self,
        course_id: str,
        location_id: str,
        course_number: str | None = None,
        course_name: str | None = None,
    ) -> None:
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
        super().__init__(course_id, location_id, course_number, course_name)
        self.course_id = course_id
        self.location_id = location_id
        self.course_number = course_number
        self.course_name = course_name

    @classmethod
    def from_dn(cls, dn: str, *args: Any, **kwargs: Any) -> Self:
        """
        Get AsmCourse object created from data in LDAP object.

        :param str dn: DN to the SchoolClass/Workgroup object to represent
        :return: AsmCourse instance
        :rtype: AsmCourse
        """
        lo, _po = get_ldap_connection()
        try:
            school_class = SchoolClass.from_dn(dn, None, lo)
        except UnknownModel:
            school_class = WorkGroup.from_dn(dn, None, lo)

        course_pattern = get_ucr().get("asm/attributes/course-name-pattern", "{ou}-{name}")
        try:
            name = school_class.name.split("-", 1)[1]
        except IndexError:
            logger = logging.getLogger(__name__)
            logger.warning(f"{dn}: course {school_class.name!r} is missing an OU")
            name = school_class.name
        course_name = course_pattern.replace("{ou}", school_class.school).replace("{name}", name)
        return cls(
            course_id=school_class.name,
            location_id=school_class.school,
            course_number=school_class.name,
            course_name=course_name,
        )
