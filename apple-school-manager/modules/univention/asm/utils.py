# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Utility functions.
"""

from functools import cache

from ucsschool.importer.utils.ldap_connection import get_machine_connection, get_readonly_connection
from ucsschool.lib.roles import context_type_school, create_ucsschool_role_string, role_dc_slave
from univention.admin.uldap import access as LoType  # noqa: N812
from univention.admin.uldap import position as PoType  # noqa: N812
from univention.config_registry import ConfigRegistry

_ucr: ConfigRegistry = None


UCS_ROLE__EMPTY_CONTEXT_VALUE = "-"


def get_ldap_connection() -> tuple[LoType, PoType]:
    if get_ucr()["server/role"] in ("domaincontroller_master", "domaincontroller_backup"):
        lo, po = get_readonly_connection()
    else:
        lo, po = get_machine_connection()
    return lo, po


def get_ucr() -> ConfigRegistry:
    global _ucr
    if not _ucr:
        _ucr = update_ucr()
    return _ucr


def update_ucr() -> ConfigRegistry:
    global _ucr
    if not _ucr:
        _ucr = ConfigRegistry()
    _ucr.load()
    return _ucr


def prepend_to_mail_domain(email: str, subdomain: str) -> str:
    """
    Prepend `subdomain` to the domain in an email address.

    :param str email: email address
    :param str subdomain: subdomain to prepend, the setting ``email_prepend_domain``
    :return: if `subdomain` is set: modified email address, else unchanged email
    :rtype: str
    """
    if not email:
        return email
    if subdomain:
        local_part, domain = split_email(email)
        return f"{local_part}@{subdomain}.{domain}"
    return email


def split_email(email: str) -> tuple[str, str]:
    local_part, at, domain = email.rpartition("@")
    if not all((local_part, at, domain)) or "." not in domain:
        msg = f"Invalid email address: {email!r}."
        raise ValueError(msg)
    return local_part, domain


def get_person_id(
    dn: str,
    person_id_attribute: str,
    additional_attrs: list[str],
) -> tuple[str, dict[str, list[str]]]:
    """
    Read the ``person_id`` and `additional_attrs` of a user from LDAP.

    :param str dn: DN of the user
    :param str person_id_attribute: LDAP attribute that holds the ``person_id``,
        the setting ``person_id_attribute``
    :param additional_attrs: further LDAP attributes to read
    :return: `person_id_attribute` and the attributes that were read
    :raises ValueError: if the user has no value in `person_id_attribute`
    """
    attrs = list(map(str, [person_id_attribute, *(additional_attrs or [])]))
    lo, _po = get_ldap_connection()
    res = lo.get(dn, attrs)
    res = {k: [v.decode("utf-8")] for k, [v] in res.items()}  # byte2str for python-ldap
    if not res.get(person_id_attribute):
        msg = f"Attribute {person_id_attribute!r} (person_id_attribute) is not set or empty on {dn!r}."
        raise ValueError(msg)
    return person_id_attribute, res


@cache
def is_central_replica() -> bool:
    """
    Check if the current server is the central replica.

    :return: whether the current server is the central replica
    :rtype: bool
    """
    ucr = get_ucr()

    if ucr.get("server/role") != "domaincontroller_slave":
        return False

    def _gather_roles() -> list[str]:
        host_dn = ucr.get("ldap/hostdn")
        ldap, _ = get_ldap_connection()
        roles = ldap.getAttr(
            host_dn,
            attr="ucsschoolRole",
            required=True,
        )
        if len(roles) < 1:
            msg = f"No ucsschoolRole set for {host_dn!r}."
            raise ValueError(msg)
        return [str(role.decode("utf-8")) for role in roles]

    roles = _gather_roles()
    return any(
        role
        == create_ucsschool_role_string(
            role_dc_slave, UCS_ROLE__EMPTY_CONTEXT_VALUE, context_type_school
        )
        for role in roles
    )
