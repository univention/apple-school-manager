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

Base class for all ASM models.
"""

import inspect
from collections.abc import Iterable
from typing import Any, Self

from univention.asm.utils import get_ucr


class AsmModel:
    """Base class for all ASM models."""

    header: list[str] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __repr__(self) -> str:
        if not self.header:
            members = [
                m
                for m in inspect.getmembers(self, predicate=lambda x: not inspect.ismethod(x))
                if not m[0].startswith("_") and m[0] != "header"
            ]
        else:
            members = list(zip(self.header, [getattr(self, m) for m in self.header], strict=False))
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(f"{k}={v!r}" for k, v in members),
        )

    def get_header(self) -> Iterable[str]:
        """
        Get the header for a CSV representation of the object.

        :return: CSV header as list of strings
        :rtype: list(str)
        """
        return self.header

    @classmethod
    def from_dn(cls, dn: str, *args: Any, **kwargs: Any) -> Self:
        """
        Get AsmModel object created from data in LDAP object.

        :param str dn: DN to object to represent
        :return: AsmModel instance
        :rtype: AsmModel
        """
        raise NotImplementedError

    def as_csv_line(self) -> Iterable[str]:
        """
        Get this object represented as a list of strings.

        This default implementation will work as long as names returned by
        :py:meth:`get_header()` match member names.

        :return: CSV line as list
        :rtype: list(str)
        """
        try:
            return [getattr(self, member) or "" for member in self.get_header()]
        except AttributeError:
            msg = f"Default implementation of as_csv_line() cannot handle {self.__class__.__name__} object."
            raise NotImplementedError(
                msg,
            )

    def as_dict(self) -> dict[str, str]:
        """
        Get this object represented as a dict of strings.

        This default implementation will work as long as names returned by
        :py:meth:`get_header()` match member names.

        :return: dictionary with header names as keys and object values
        :rtype: dict(str)
        """
        try:
            return {member: getattr(self, member) or "" for member in self.get_header()}
        except AttributeError:
            msg = f"Default implementation of as_csv_line() cannot handle {self.__class__.__name__} object."
            raise NotImplementedError(
                msg,
            )


class AnonymizeMixIn:
    ucr_anonymize_key_base = ""

    @classmethod
    def anonymize(cls, user: AsmModel, ldap_attrs: dict[str, Any], **kwargs: Any) -> dict[str, str]:
        """
        Change values of function arguments to anonymize/pseudonymize user if
        UCRV asm/attributes/<staff/student>/anonymize is true. Will return
        unchanged function arguments otherwise.

        :param User user: user object
        :param dict ldap_attrs: dictionary with the users LDAP attributes
        :return: dictionary with [modified] function arguments
        :rtype: dict
        :raises NotImplementedError: if cls.ucr_anonymize_key_base is unset
        """
        ucr = get_ucr()
        if ucr.is_true(cls.ucr_anonymize_key_base):
            for k, v in list(cls.anonymize_mapping().items()):
                if v and v.startswith("%"):
                    attr = v[1:].strip()
                    try:
                        v = ldap_attrs[attr][0]
                    except KeyError:
                        msg = f"Attribute {attr!r} not found in LDAP object of {user}."
                        raise ValueError(msg)
                    except IndexError:
                        msg = f"Attribute {attr!r} empty in LDAP object of {user}."
                        raise ValueError(msg)
                kwargs[k] = v
        return kwargs

    @classmethod
    def anonymize_mapping(cls) -> dict[str, str | None]:
        if not cls.ucr_anonymize_key_base:
            msg = 'Class attribute "ucr_anonymize_key_base" must be set.'
            raise NotImplementedError(msg)
        cls.ucr_anonymize_key_base = cls.ucr_anonymize_key_base.rstrip("/")
        ucr = get_ucr()
        return {
            "first_name": ucr.get(f"{cls.ucr_anonymize_key_base}/first_name", "%uid"),
            "middle_name": ucr.get(f"{cls.ucr_anonymize_key_base}/middle_name", None),
            "last_name": ucr.get(f"{cls.ucr_anonymize_key_base}/last_name", "No Name"),
            "email_address": ucr.get(f"{cls.ucr_anonymize_key_base}/email_address", None),
            "sis_username": ucr.get(f"{cls.ucr_anonymize_key_base}/sis_username", "%uid"),
        }
