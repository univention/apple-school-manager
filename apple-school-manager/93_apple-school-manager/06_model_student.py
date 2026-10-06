#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test student model/CSV generation
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
from ucsschool.lib.models.user import Student
from univention.admin.uldap import access
from univention.asm.config import DEFAULT_ANONYMIZE_VALUES, Settings, StudentSettings
from univention.asm.models.student import AsmStudent
from univention.asm.utils import get_person_id
from univention.testing import utils
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

log = logging.getLogger(__name__)


def test_default_password_policy() -> None:
    assert StudentSettings().password_policy == 4, (
        f"Default password_policy is {StudentSettings().password_policy!r}, expected 4."
    )


def test_student_csv_line(
    schoolenv: UCSTestSchool,
    lo: access,
    create_ous: Callable[..., list[tuple[str, str]]],
    maildomain: str,
) -> None:
    (school1, _), (school2, _) = create_ous(2)
    subdomain = uts.random_name()
    settings = Settings(email_prepend_domain=subdomain, student=StudentSettings(anonymize=False))

    student1_name, student1_dn = schoolenv.create_student(school1)
    email_local = uts.random_name()
    email = f"{email_local}@{maildomain}"
    email_sub = f"{email_local}@{subdomain}.{maildomain}"
    student2_name, student2_dn = schoolenv.create_student(
        school2,
        schools=[school1, school2],
        mailaddress=email,
    )
    log.info("Created student1: %r (%s)", student1_name, student1_dn)
    log.info("Created student2: %r (%s)", student2_name, student2_dn)

    # check if this system has a schema that supports a middle name
    student1 = Student.from_dn(student1_dn, None, lo)
    student_udm_obj = student1.get_udm_object(lo)
    for attr in ("middleName", "initials", "oxMiddleName"):
        if attr in student_udm_obj:
            middle_name = uts.random_name(length=5)
            log.info("*** Adding middle name to student1: %r...", middle_name)
            student_udm_obj[attr] = middle_name
            student_udm_obj.modify()
            utils.verify_ldap_object(student1_dn, {attr: [middle_name]})
            # reload object just to be safe
            student1 = Student.from_dn(student1_dn, None, lo)
            break
    else:
        log.info("*** No LDAP schema for middle name attribute found.")
        middle_name = ""

    student2 = Student.from_dn(student2_dn, None, lo)

    s1_id_attr, s1_lo = get_person_id(student1_dn, "entryUUID", [])
    s1_name = s1_lo[s1_id_attr][0]
    s2_id_attr, s2_lo = get_person_id(student2_dn, "entryUUID", [])
    s2_name = s2_lo[s2_id_attr][0]

    got_student1 = AsmStudent.from_dn(student1_dn, settings).as_csv_line()
    expected_student1 = [
        s1_name,
        s1_name,
        student1.firstname,
        middle_name,
        student1.lastname,
        "",  # grade level
        "",
        student1_name,
        "4",
        school1,
    ]
    assert got_student1 == expected_student1, (
        f"CSV line for student1,\nexp: {expected_student1!r}\ngot: {got_student1!r}."
    )

    settings = Settings(
        email_prepend_domain=subdomain,
        student=StudentSettings(anonymize=False, grade_level_attribute="sn"),
    )
    got_student1 = AsmStudent.from_dn(student1_dn, settings).as_csv_line()
    expected_student1 = [
        s1_name,
        s1_name,
        student1.firstname,
        middle_name,
        student1.lastname,
        student1.lastname,  # grade level
        "",
        student1_name,
        "4",
        school1,
    ]
    assert got_student1 == expected_student1, (
        f"CSV line for student1,\nexp: {expected_student1!r}\ngot: {got_student1!r}."
    )

    settings = Settings(
        email_prepend_domain=subdomain,
        student=StudentSettings(anonymize=False, grade_level_attribute="sn", password_policy=None),
    )
    got_student2 = AsmStudent.from_dn(student2_dn, settings).as_csv_line()
    expected_student2 = [
        s2_name,
        s2_name,
        student2.firstname,
        "",
        student2.lastname,
        student2.lastname,  # grade level
        email_sub,
        student2_name,
        "",
        school2,
        school1,
    ]
    assert got_student2 == expected_student2, (
        f"CSV line for student2,\nexp: {expected_student2!r}\ngot: {got_student2!r}."
    )

    settings = Settings(
        email_prepend_domain=subdomain,
        student=StudentSettings(anonymize=True, grade_level_attribute="sn", password_policy=6),
    )
    got_student1 = AsmStudent.from_dn(student1_dn, settings).as_csv_line()
    expected_student1 = [
        s1_name,
        s1_name,
        student1.name,
        "",
        "-",
        student1.lastname,  # grade level
        "",
        student1.name,
        "6",
        school1,
    ]
    assert got_student1 == expected_student1, (
        f"CSV line for student1 anonymized,\nexp: {expected_student1!r}\ngot: {got_student1!r}."
    )

    last_name_anon = uts.random_name()
    settings = Settings(
        email_prepend_domain=subdomain,
        student=StudentSettings(
            anonymize=True,
            anonymize_values={**DEFAULT_ANONYMIZE_VALUES, "last_name": last_name_anon},
            grade_level_attribute="sn",
            password_policy=8,
        ),
    )
    got_student1 = AsmStudent.from_dn(student1_dn, settings).as_csv_line()
    expected_student1 = [
        s1_name,
        s1_name,
        student1.name,
        "",
        last_name_anon,
        student1.lastname,  # grade level
        "",
        student1.name,
        "8",
        school1,
    ]
    assert got_student1 == expected_student1, (
        f"CSV line with static last_name for student1 anonymized,\nexp: {expected_student1!r}\ngot: {got_student1!r}."
    )
