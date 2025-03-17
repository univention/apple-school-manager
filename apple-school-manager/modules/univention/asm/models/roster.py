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
Univention Apple School Manager Connector.

Class to represent an ASM roster.

See https://support.apple.com/en-us/HT207029
"""

from typing import Any, Self

from ucsschool.lib.models.base import UnknownModel
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.user import Student

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
    def from_dn(cls, dn: str, student_dn: str, *args: Any, **kwargs: Any) -> Self:
        """
        Get AsmRoster object created from data in LDAP object.

        :param str dn: DN to the SchoolClass/Workgroup object to represent
        :param str student_dn: DN to the student object to represent
        :return: AsmRoster instance
        :rtype: AsmRoster
        """
        lo, po = get_ldap_connection()
        try:
            school_class = SchoolClass.from_dn(dn, None, lo)
        except UnknownModel:
            school_class = WorkGroup.from_dn(dn, None, lo)
        student = Student.from_dn(student_dn, None, lo)
        person_id_attr, student_lo = get_person_id(student.dn, "student", [])
        person_id = student_lo[person_id_attr][0]
        return cls(
            roster_id=f"{school_class.name}-{person_id}",
            class_id=school_class.name,
            student_id=person_id,
        )
