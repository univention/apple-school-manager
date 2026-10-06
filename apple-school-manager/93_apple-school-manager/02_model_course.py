#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test course model/CSV generation
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
from ucsschool.lib.models.group import SchoolClass
from univention.admin.uldap import access
from univention.asm.config import SchoolSettings, Settings
from univention.asm.models.course import AsmCourse
from univention.testing import utils
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

log = logging.getLogger(__name__)


def get_course_name(course_pattern: str, school: str, name: str) -> str:
    return course_pattern.format(ou=school, name=name)


def group_members(lo: access, name: str) -> list[tuple[str, dict[str, list[bytes]]]]:
    members: list[tuple[str, dict[str, list[bytes]]]] = lo.search(
        filter_format("(&(objectClass=univentionGroup)(cn=%s))", (name,)),
        attr=["memberUid"],
    )
    return members


def find_group_dn(lo: access, name: str, label: str) -> str:
    filter_s = filter_format("(&(objectClass=univentionGroup)(cn=%s))", (name,))
    res = lo.searchDn(filter=filter_s)
    assert len(res) == 1, (
        f"{label} not found: search with filter={filter_s!r} did not return 1 result:\n{res}"
    )
    dn: str = res[0]
    return dn


def test_course_csv_line(
    schoolenv: UCSTestSchool,
    lo: access,
    create_ous: Callable[..., list[tuple[str, str]]],
) -> None:
    [(ou_name, _ou_dn)] = create_ous(1)
    school_class1 = f"{ou_name}-{uts.random_username()}"
    school_class2 = f"{ou_name}-{uts.random_username()}"

    log.info(
        "*** Creating a teacher with 2 school_classes: %r %r...",
        school_class1,
        school_class2,
    )
    teacher1_name, teacher1_dn = schoolenv.create_teacher(
        ou_name,
        classes=f"{school_class1},{school_class2}",
    )
    work_group1_description = uts.random_name()
    work_group1_name, work_group1_dn = schoolenv.create_workgroup(
        ou_name,
        description=work_group1_description,
        users=[teacher1_dn],
    )
    log.info("Created teacher1: %r (%s)", teacher1_name, teacher1_dn)
    log.info("Created school_class1=%r", group_members(lo, school_class1))
    log.info("Created school_class2=%r", group_members(lo, school_class1))
    log.info("Created work_group1=%r", group_members(lo, work_group1_name))

    school_class1_dn = find_group_dn(lo, school_class1, "School class 1")
    utils.verify_ldap_object(school_class1_dn, {"memberUid": [teacher1_name]})

    school_class2_dn = find_group_dn(lo, school_class2, "School class 2")
    utils.verify_ldap_object(school_class2_dn, {"memberUid": [teacher1_name]})

    description = uts.random_string()
    log.info("*** Adding description to school_class2: %r...", description)
    sc2 = SchoolClass.from_dn(school_class2_dn, ou_name, lo)
    sc2.description = description
    sc2.modify(lo)
    utils.verify_ldap_object(
        school_class2_dn,
        {"memberUid": [teacher1_name], "description": [description]},
    )

    utils.verify_ldap_object(work_group1_dn, {"memberUid": [teacher1_name]})

    for course_pattern in ["{name}", "{ou}-{name}", "{name}-{random}-{ou}"]:
        course_pattern = course_pattern.replace("{random}", uts.random_string())
        settings = Settings(
            schools={ou_name: SchoolSettings(course_name_pattern=course_pattern)},
            other_schools=None,
        )

        got_course1 = AsmCourse.from_dn(school_class1_dn, settings).as_csv_line()
        school, school_class1_name = school_class1.split("-", 1)
        course_name = get_course_name(course_pattern, school, school_class1_name)
        expected_course1 = [school_class1, school_class1, course_name, ou_name]
        assert got_course1 == expected_course1, (
            f"Expected CSV line for course1: {expected_course1!r}, got: {got_course1!r}."
        )

        got_course2 = AsmCourse.from_dn(school_class2_dn, settings).as_csv_line()
        school, school_class2_name = school_class2.split("-", 1)
        course_name = get_course_name(course_pattern, school, school_class2_name)
        expected_course2 = [school_class2, school_class2, course_name, ou_name]
        assert got_course2 == expected_course2, (
            f"Expected CSV line for course2: {expected_course2!r}, got: {got_course2!r}."
        )

        got_workgroup1 = AsmCourse.from_dn(work_group1_dn, settings).as_csv_line()
        _work_group1_name = work_group1_name.split("-", 1)[1]
        course_name = get_course_name(course_pattern, ou_name, _work_group1_name)
        expected_workgroup1 = [work_group1_name, work_group1_name, course_name, ou_name]
        assert got_workgroup1 == expected_workgroup1, (
            f"Expected CSV line for workgroup1: {expected_workgroup1!r}, got: {got_workgroup1!r}."
        )
