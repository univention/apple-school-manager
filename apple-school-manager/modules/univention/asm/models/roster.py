# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Class to represent an ASM roster.

See https://support.apple.com/en-us/HT207029
"""

from typing import Any, Self

from ucsschool.lib.models.base import UnknownModel
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.user import Student

from univention.asm.config import Settings
from univention.asm.utils import get_ldap_connection, get_person_id

from .base import AsmModel


class AsmRoster(AsmModel):
    """Class to represent an ASM roster entry."""

    header = ["roster_id", "class_id", "student_id"]

    def __init__(
        self,
        roster_id: str,
        class_id: str,
        student_id: str,
    ) -> None:
        """
        :param str roster_id: A unique identifier for the roster in your SIS
                or other course database (if available) (required).
        :param str class_id: A unique alphanumeric identifier for the class.
                This must match a class_id in the Class file (required).
        :param str student_id: A person_id for one student (required).
        """
        super().__init__(roster_id, class_id, student_id)
        self.roster_id = roster_id
        self.class_id = class_id
        self.student_id = student_id

    @classmethod
    def from_dn(
        cls,
        dn: str,
        student_dn: str,
        settings: Settings | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Self:
        """
        Get AsmRoster object created from data in LDAP object.

        :param str dn: DN to the SchoolClass/Workgroup object to represent
        :param str student_dn: DN to the student object to represent
        :param settings: settings of the Apple School Manager account, the
                default settings if None
        :return: AsmRoster instance
        :rtype: AsmRoster
        """
        settings = settings or Settings()
        lo, _po = get_ldap_connection()
        try:
            school_class = SchoolClass.from_dn(dn, None, lo)
        except UnknownModel:
            school_class = WorkGroup.from_dn(dn, None, lo)
        student = Student.from_dn(student_dn, None, lo)
        person_id_attr, student_lo = get_person_id(student.dn, settings.student.person_id_attribute, [])
        person_id = student_lo[person_id_attr][0]
        return cls(
            roster_id=f"{school_class.name}-{person_id}",
            class_id=school_class.name,
            student_id=person_id,
        )
