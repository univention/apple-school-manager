#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test roster model/CSV generation
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
from univention.admin.uldap import access
from univention.asm.models.roster import AsmRoster
from univention.asm.utils import get_person_id
from univention.testing import utils
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

log = logging.getLogger(__name__)


def person_id(dn: str) -> str:
    id_attr, attrs = get_person_id(dn, "entryUUID", [])
    name: str = attrs[id_attr][0]
    return name


def group_members(lo: access, name: str) -> list[tuple[str, dict[str, list[bytes]]]]:
    members: list[tuple[str, dict[str, list[bytes]]]] = lo.search(
        filter_format("(&(objectClass=univentionGroup)(cn=%s))", (name,)),
        attr=["memberUid"],
    )
    return members


def test_roster_csv_line(
    schoolenv: UCSTestSchool,
    lo: access,
    create_ous: Callable[..., list[tuple[str, str]]],
) -> None:
    [(school1, _ou_dn)] = create_ous(1)
    school_class1 = f"{school1}-{uts.random_username()}"

    log.info("*** Creating two students in same school_class and workgroup: %r...", school_class1)
    student1_name, student1_dn = schoolenv.create_student(school1, classes=school_class1)
    student2_name, student2_dn = schoolenv.create_student(school1, classes=school_class1)
    # "users" are created in the reverse order!?!?!?!
    s1_name = person_id(student1_dn)
    s2_name = person_id(student2_dn)
    work_group1_description = uts.random_name()
    work_group1_name, work_group1_dn = schoolenv.create_workgroup(
        school1,
        description=work_group1_description,
        users=[student2_dn, student1_dn],
    )
    log.info("Created student1: %r (%s, %s)", student1_name, student1_dn, s1_name)
    log.info("Created student2: %r (%s, %s)", student2_name, student2_dn, s2_name)
    log.info("Created school_class1=%r", group_members(lo, school_class1))
    log.info("Created work_group1=%r", group_members(lo, work_group1_name))

    filter_s = filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class1,))
    res = lo.searchDn(filter=filter_s)
    assert len(res) == 1, (
        f"School class 1 not found: search with filter={filter_s!r} did not return 1 result:\n{res}"
    )
    school_class1_dn = res[0]
    utils.verify_ldap_object(school_class1_dn, {"memberUid": [student1_name, student2_name]})

    utils.verify_ldap_object(work_group1_dn, {"memberUid": [student1_name, student2_name]})

    got_roster1 = AsmRoster.from_dn(dn=school_class1_dn, student_dn=student1_dn).as_csv_line()
    expected_roster1 = [f"{school_class1}-{s1_name}", school_class1, s1_name]
    assert got_roster1 == expected_roster1, (
        f"Expected CSV line for roster1: {expected_roster1!r}, got: {got_roster1!r}."
    )

    got_roster2 = AsmRoster.from_dn(dn=school_class1_dn, student_dn=student2_dn).as_csv_line()
    expected_roster2 = [f"{school_class1}-{s2_name}", school_class1, s2_name]
    assert got_roster2 == expected_roster2, (
        f"Expected CSV line for roster2: {expected_roster2!r}, got: {got_roster2!r}."
    )

    got_workgroup1 = AsmRoster.from_dn(dn=work_group1_dn, student_dn=student2_dn).as_csv_line()
    expected_workgroup1 = [f"{work_group1_name}-{s2_name}", work_group1_name, s2_name]
    assert got_workgroup1 == expected_workgroup1, (
        f"Expected CSV line for workgroup1: {expected_workgroup1!r}, got: {got_workgroup1!r}."
    )
