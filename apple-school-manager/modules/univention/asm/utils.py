# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Utility functions.
"""

# don't import __future__.unicode_literals here, DNS lib cannot handle it!

from functools import cache

import DNS
from ucsschool.importer.utils.ldap_connection import get_machine_connection, get_readonly_connection
from ucsschool.lib.roles import context_type_school, create_ucsschool_role_string, role_dc_slave

from univention.admin.uldap import access as LoType  # noqa: N812
from univention.admin.uldap import position as PoType  # noqa: N812
from univention.config_registry import ConfigRegistry

_external_dns_resolvers: list[str] = []
_known_domains: dict[str, bool] = {}
_ucr: ConfigRegistry = None


UCS_ROLE__EMPTY_CONTEXT_VALUE = "-"


def get_ldap_connection() -> tuple[LoType, PoType]:
    if get_ucr()["server/role"] in ("domaincontroller_master", "domaincontroller_backup"):
        lo, po = get_readonly_connection()
    else:
        lo, po = get_machine_connection()
    return lo, po


def check_domain(email: str) -> bool:
    """
    Verify that the second level domain in ``email`` exists.

    :param str email: an email address
    :return: whether the second level domain in the email addresses domain exists
    :rtype: bool
    :raises ValueError: if the email address has an invalid format
    """
    _local_part, domain = split_email(email)
    domain_to_check = ".".join(domain.split(".")[-2:])
    if domain_to_check not in _known_domains:
        dns_servers = get_static_dns_resolvers()
        requester = DNS.DnsRequest(server=dns_servers, timeout=5)
        dns_result: DNS.Lib.DnsResult = requester.req(name=str(domain_to_check), qtype="A")
        _known_domains[domain_to_check] = bool(dns_result.answers)
    return _known_domains[domain_to_check]


def get_static_dns_resolvers() -> list[str]:
    """
    Get external DNS resolvers from UCR.

    :return: list of IP addresses
    :rtype: list(str)
    """
    if not _external_dns_resolvers:
        ucr = get_ucr()
        _external_dns_resolvers.extend(
            [
                ns
                for ns in (
                    ucr.get("dns/forwarder1", ""),
                    ucr.get("dns/forwarder2", ""),
                    ucr.get("dns/forwarder3", ""),
                )
                if ns.strip()
            ],
        )
    return _external_dns_resolvers


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


def prepend_to_mail_domain(email: str) -> str:
    """
    Prepend subdomain from UCRV
    ``asm/attributes/user/email/prepend_domain`` to domain in email
    address.

    :param str email: email address
    :return: if UCRV is set: modified email address, else unchanged email
    :rtype: str
    """
    if not email:
        return email
    ucr = get_ucr()
    subdomain = ucr.get("asm/attributes/user/email/prepend_domain", "").strip(" .")
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


def get_person_id(dn: str, role: str, additional_attrs: list[str]) -> tuple[str, dict[str, str]]:
    if role not in ("staff", "student"):
        msg = f"role {role!r} must be 'staff' or 'student'."
        raise ValueError(msg)
    additional_attrs = additional_attrs or []
    ucrv = f"asm/attributes/{role}/person_id/mapping"
    person_id_attr = get_ucr().get(ucrv, "%entryUUID")
    person_id_attr = person_id_attr[1:].strip()
    attrs = list(map(str, [person_id_attr, *additional_attrs]))  # unicode2str for python-ldap
    lo, _po = get_ldap_connection()
    res = lo.get(dn, attrs)
    res = {k: [v.decode("utf-8")] for k, [v] in res.items()}  # byte2str for python-ldap
    if not res.get(person_id_attr):
        msg = f"Attribute {person_id_attr!r} from {ucrv!r} is not set or empty on {dn!r}."
        raise ValueError(msg)
    return person_id_attr, res


def get_default_password_policy() -> str:
    ucr = get_ucr()
    pp_ori = ucr.get("asm/attributes/student/password_policy", 4)
    try:
        pp = "" if pp_ori == "-" else int(pp_ori)
        if pp not in (4, 6, 8, ""):
            raise ValueError
    except ValueError:
        msg = f"Value of UCR asm/attributes/student/password_policy must be 4, 6, 8 or '-' (found {pp_ori!r})."
        raise ValueError(
            msg,
        )
    return str(pp)


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
