#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test class model/CSV generation
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622, 48511]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only


import logging
import random
from collections.abc import Callable

import univention.testing.strings as uts
from ldap.filter import filter_format
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.user import User
from univention.admin.uldap import access
from univention.asm.models.classes import AsmClass
from univention.asm.models.staff import get_filtered_staff
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


def find_group_dn(lo: access, name: str, label: str) -> str:
    filter_s = filter_format("(&(objectClass=univentionGroup)(cn=%s))", (name,))
    res = lo.searchDn(filter=filter_s)
    assert len(res) == 1, (
        f"{label} not found: search with filter={filter_s!r} did not return 1 result:\n{res}"
    )
    dn: str = res[0]
    return dn


def test_class_csv_line(
    schoolenv: UCSTestSchool,
    lo: access,
    create_ous: Callable[..., list[tuple[str, str]]],
) -> None:
    ous = [name for name, _dn in create_ous(2)]
    random.shuffle(ous)
    school1 = ous[0]
    school2 = ous[1]
    schools = [school1, school2]
    school_class1 = f"{school1}-{uts.random_username()}"
    school_class2 = f"{school2}-{uts.random_username()}"

    log.info("*** Creating users: 1x staff, 1x teacher 1x teacher+staff, 2x student...")
    log.info(f"*** school1={school1!r} school2={school2!r} ...")
    log.info(f"*** school_class1={school_class1!r} school_class2={school_class2!r} ...")
    staff1_name, staff1_dn = schoolenv.create_staff(random.choice(ous))
    teacher1_name, teacher1_dn = schoolenv.create_teacher(
        school1,
        schools=schools,
        classes=f"{school_class1},{school_class2}",
    )
    teacher2_name, teacher2_dn = schoolenv.create_teacher_and_staff(
        school1,
        classes=school_class1,
    )
    teacher3_name, teacher3_dn = schoolenv.create_teacher_and_staff(
        school1,
        classes=school_class1,
    )
    teacher4_name, teacher4_dn = schoolenv.create_teacher_and_staff(
        school1,
        classes=school_class1,
    )
    teacher5_name, teacher5_dn = schoolenv.create_teacher_and_staff(
        school1,
        classes=school_class1,
    )
    student1_name, student1_dn = schoolenv.create_student(school1, classes=school_class1)
    student2_name, student2_dn = schoolenv.create_student(school2, classes=school_class2)
    # "users" are created in the reverse order!?!?!?!
    t1_name = person_id(teacher1_dn)
    t2_name = person_id(teacher2_dn)
    t3_name = person_id(teacher3_dn)
    t4_name = person_id(teacher4_dn)
    t5_name = person_id(teacher5_dn)
    work_group1_name, work_group1_dn = schoolenv.create_workgroup(
        school1,
        description=f"The description {school1}",
        users=[teacher2_dn, teacher1_dn, student1_dn],
    )
    work_group2_name, work_group2_dn = schoolenv.create_workgroup(
        school2,
        description=f"The description {school2}",
        users=[student2_dn],
    )

    log.info("Created staff1: %r (%s)", staff1_name, staff1_dn)
    log.info("Created teacher1: %r (%s, %s)", teacher1_name, teacher1_dn, t1_name)
    log.info("Created teacher2: %r (%s, %s)", teacher2_name, teacher2_dn, t2_name)
    log.info("Created teacher3: %r (%s, %s)", teacher3_name, teacher3_dn, t3_name)
    log.info("Created teacher4: %r (%s, %s)", teacher4_name, teacher4_dn, t4_name)
    log.info("Created teacher5: %r (%s, %s)", teacher5_name, teacher5_dn, t5_name)
    log.info("Created student1: %r (%s)", student1_name, student1_dn)
    log.info("Created student2: %r (%s)", student2_name, student2_dn)
    log.info("Created school_class1=%r", group_members(lo, school_class1))
    log.info("Created school_class2=%r", group_members(lo, school_class2))
    log.info("Created work_group1=%r", group_members(lo, work_group1_name))
    log.info("Created work_group2=%r", group_members(lo, work_group2_name))

    school_class1_dn = find_group_dn(lo, school_class1, "School class 1")
    utils.verify_ldap_object(
        school_class1_dn,
        {
            "memberUid": [
                teacher1_name,
                teacher2_name,
                teacher3_name,
                teacher4_name,
                teacher5_name,
                student1_name,
            ],
        },
    )

    school_class2_dn = find_group_dn(lo, school_class2, "School class 2")
    utils.verify_ldap_object(school_class2_dn, {"memberUid": [teacher1_name, student2_name]})

    utils.verify_ldap_object(
        work_group1_dn,
        {"memberUid": [student1_name, teacher1_name, teacher2_name]},
    )
    utils.verify_ldap_object(work_group2_dn, {"memberUid": [student2_name]})

    got_school_class1 = AsmClass.from_dn(school_class1_dn).as_csv_line()
    expected_school_class1 = [
        school_class1,
        "",
        school_class1,
        t1_name,
        t2_name,
        t3_name,
        school1,
        t4_name,
        t5_name,
    ]
    assert got_school_class1 == expected_school_class1, (
        f"Expected CSV line for school_class1: {expected_school_class1!r}, got: {got_school_class1!r}."
    )

    got_school_class2 = AsmClass.from_dn(school_class2_dn).as_csv_line()
    expected_school_class2 = [school_class2, "", school_class2, t1_name, "", "", school2]
    assert got_school_class2 == expected_school_class2, (
        f"Expected CSV line for school_class2: {expected_school_class2!r}, got: {got_school_class2!r}."
    )

    got_wg1 = AsmClass.from_dn(work_group1_dn).as_csv_line()
    expected_wg1 = (  # handle random user order
        [work_group1_name, "", work_group1_name, t1_name, t2_name, "", school1],
        [work_group1_name, "", work_group1_name, t2_name, t1_name, "", school1],
    )
    assert got_wg1 in expected_wg1, (
        f"Expected CSV line for work_group1: {expected_wg1!r}, got: {got_wg1!r}."
    )

    got_wg2 = AsmClass.from_dn(work_group2_dn).as_csv_line()
    expected_wg2 = [work_group2_name, "", work_group2_name, "", "", "", school2]
    assert got_wg2 == expected_wg2, (
        f"Expected CSV line for work_group2: {expected_wg2!r}, got: {got_wg2!r}."
    )

    # Bug #48511: not more than 3+12=15 instructors per class
    # school_class1 has 5 teachers now. adding 11.
    # the CSV should only contain 3+12=15 instructors and ignore 1 teacher.
    new_teacher_dns = []
    for _i in range(11):
        teacher_name, teacher_dn = schoolenv.create_teacher_and_staff(
            school1,
            classes=school_class1,
        )
        new_teacher_dns.append(teacher_dn)
        log.info("Added teacher %r to %r.", teacher_name, school_class1)
    log.info(
        "Members of %r (school_class1) now: %r",
        school_class1,
        group_members(lo, school_class1)[0][1]["memberUid"],
    )

    teacher_count = 0
    sc1 = SchoolClass.from_dn(school_class1_dn, school1, lo)
    for user_dn in sc1.users:
        user = User.from_dn(user_dn, school1, lo)
        if user.is_teacher(lo):
            teacher_count += 1
    log.info("Counted %d teachers in %r (school_class1).", teacher_count, school_class1)
    get_filtered_staff.cache_clear()
    got_school_class1 = AsmClass.from_dn(school_class1_dn).as_csv_line()
    expected_school_class1.extend(
        person_id(t_dn) for t_dn in new_teacher_dns[:10]
    )  # <-- dropping last teacher!
    assert got_school_class1 == expected_school_class1, (
        f"Expected CSV line for school_class1: {expected_school_class1!r}, got: {got_school_class1!r}."
    )
