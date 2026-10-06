#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test location model/CSV generation
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import logging
from collections.abc import Callable

import univention.testing.strings as uts
from ldap.filter import filter_format
from ucsschool.lib.models.school import School
from univention.admin.uldap import access
from univention.asm.models.location import AsmLocation
from univention.testing import utils

log = logging.getLogger(__name__)


def test_location_csv_line(lo: access, create_ous: Callable[..., list[tuple[str, str]]]) -> None:
    [(school1, _dn1), (school2, _dn2)] = create_ous(2)

    filter_s = filter_format("(&(objectClass=ucsschoolOrganizationalUnit)(ou=%s))", (school1,))
    res = lo.search(filter=filter_s)
    assert len(res) == 1, (
        f"School 1 not found: search with filter={filter_s!r} did not return 1 result:\n{res}"
    )
    school1_dn = res[0][0]
    school1_attrs = res[0][1]

    filter_s = filter_format("(&(objectClass=ucsschoolOrganizationalUnit)(ou=%s))", (school2,))
    res = lo.searchDn(filter=filter_s)
    assert len(res) == 1, (
        f"School 2 not found: search with filter={filter_s!r} did not return 1 result:\n{res}"
    )
    school2_dn = res[0]

    display_name = uts.random_string()
    log.info("Setting display_name of school2 (%s) to %r.", school2, display_name)
    sc2 = School.from_dn(school2_dn, school2, lo)
    sc2.display_name = display_name
    sc2.modify(lo)
    utils.verify_ldap_object(school2_dn, {"displayName": [display_name]})

    got_loc1 = AsmLocation.from_dn(school1_dn).as_csv_line()
    expected_loc1 = [school1, school1_attrs.get("displayName", [None])[0].decode("utf-8") or school1]
    assert got_loc1 == expected_loc1, (
        f"Expected CSV line for location1: {expected_loc1!r}, got: {got_loc1!r}."
    )

    got_loc2 = AsmLocation.from_dn(school2_dn).as_csv_line()
    expected_loc2 = [school2, display_name]
    assert got_loc2 == expected_loc2, (
        f"Expected CSV line for location2: {expected_loc2!r}, got: {got_loc2!r}."
    )
