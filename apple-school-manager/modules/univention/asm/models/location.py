# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Class to represent an ASM location.

See https://support.apple.com/en-us/HT207029
"""

from typing import Any, Self

from ucsschool.lib.models.school import School

from univention.asm.utils import get_ldap_connection

from .base import AsmModel


class AsmLocation(AsmModel):
    """Class to represent an ASM location entry."""

    header = ["location_id", "location_name"]

    def __init__(self, location_id: str, location_name: str) -> None:
        """
        :param str location_id: A unique identifier made of numbers and/or
                letters that contains no spaces (required).
        :param str location_name: The name of the location (required).
        """
        super().__init__(location_id, location_name)
        self.location_id = location_id
        self.location_name = location_name

    @classmethod
    def from_dn(cls, dn: str, *args: Any, **kwargs: Any) -> Self:
        """
        Get AsmLocation object created from data in LDAP object.

        :param str dn: DN to the School/OU object to represent
        :return: AsmLocation instance
        :rtype: AsmLocation
        """
        lo, _po = get_ldap_connection()
        school = School.from_dn(dn, None, lo)
        return cls(school.name, school.display_name or school.name)
