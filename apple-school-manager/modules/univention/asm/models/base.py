# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Base class for all ASM models.
"""

import inspect
from collections.abc import Iterable
from typing import Any, Self

from univention.asm.config import RoleSettings


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
    @classmethod
    def anonymize(
        cls,
        user: AsmModel,
        ldap_attrs: dict[str, Any],
        settings: RoleSettings,
        **kwargs: Any,
    ) -> dict[str, str]:
        """
        Replace the values of the function arguments by the anonymization
        values if the setting ``anonymize`` is enabled. Will return unchanged
        function arguments otherwise.

        :param User user: user object
        :param dict ldap_attrs: dictionary with the users LDAP attributes
        :param settings: the settings of the users role
        :return: dictionary with [modified] function arguments
        :rtype: dict
        """
        if settings.anonymize:
            for k, v in settings.anonymize_values.items():
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

    @staticmethod
    def anonymize_ldap_attributes(settings: RoleSettings) -> set[str]:
        """Return the LDAP attributes that the anonymization values refer to."""
        if not settings.anonymize:
            return set()
        return {v[1:].strip() for v in settings.anonymize_values.values() if v and v.startswith("%")}
