#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test staff model/CSV generation
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
from ucsschool.lib.models.user import Teacher, TeachersAndStaff
from univention.admin.uldap import access
from univention.asm.config import DEFAULT_ANONYMIZE_VALUES, RoleSettings, Settings
from univention.asm.models.staff import AsmStaff
from univention.asm.utils import get_person_id
from univention.testing import utils
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

log = logging.getLogger(__name__)


def test_staff_csv_line(
    schoolenv: UCSTestSchool,
    lo: access,
    create_ous: Callable[..., list[tuple[str, str]]],
    maildomain: str,
) -> None:
    (school1, _), (school2, _) = create_ous(2)
    subdomain = uts.random_name()
    settings = Settings(email_prepend_domain=subdomain, staff=RoleSettings(anonymize=False))

    teacher1_name, teacher1_dn = schoolenv.create_teacher(school1)
    email_local = uts.random_name()
    email = f"{email_local}@{maildomain}"
    email_sub = f"{email_local}@{subdomain}.{maildomain}"
    teacher2_name, teacher2_dn = schoolenv.create_teacher_and_staff(
        school2,
        schools=[school1, school2],
        mailaddress=email,
    )
    t1_id_attr, t1_lo = get_person_id(teacher1_dn, "entryUUID", [])
    t1_name = t1_lo[t1_id_attr][0]
    t2_id_attr, t2_lo = get_person_id(teacher2_dn, "entryUUID", [])
    t2_name = t2_lo[t2_id_attr][0]
    log.info("Created teacher1: %r (%s, %s)", teacher1_name, teacher1_dn, t1_name)
    log.info("Created teacher2: %r (%s, %s)", teacher2_name, teacher2_dn, t2_name)

    # check if this system has a schema that supports a middle name
    teacher1 = Teacher.from_dn(teacher1_dn, None, lo)
    teacher_udm_obj = teacher1.get_udm_object(lo)
    for attr in ("middleName", "initials", "oxMiddleName"):
        if attr in teacher_udm_obj:
            middle_name = uts.random_name(length=5)
            log.info("*** Adding middle name to teacher1: %r...", middle_name)
            teacher_udm_obj[attr] = middle_name
            teacher_udm_obj.modify()
            utils.verify_ldap_object(teacher1_dn, {attr: [middle_name]})
            # reload object just to be safe
            teacher1 = Teacher.from_dn(teacher1_dn, None, lo)
            break
    else:
        log.info("*** No LDAP schema for middle name attribute found.")
        middle_name = ""

    teacher2 = TeachersAndStaff.from_dn(teacher2_dn, None, lo)

    got_teacher1 = AsmStaff.from_dn(teacher1_dn, settings).as_csv_line()
    expected_teacher1 = [
        t1_name,
        t1_name,
        teacher1.firstname,
        middle_name,
        teacher1.lastname,
        "",
        teacher1_name,
        school1,
    ]
    assert got_teacher1 == expected_teacher1, (
        f"CSV line for teacher1,\nexp: {expected_teacher1!r}\ngot: {got_teacher1!r}."
    )

    got_teacher2 = AsmStaff.from_dn(teacher2_dn, settings).as_csv_line()
    expected_teacher2 = [
        t2_name,
        t2_name,
        teacher2.firstname,
        "",
        teacher2.lastname,
        email_sub,
        teacher2_name,
        school2,
        school1,
    ]
    assert got_teacher2 == expected_teacher2, (
        f"CSV line for teacher2,\nexp: {expected_teacher2!r}\ngot: {got_teacher2!r}."
    )

    settings = Settings(email_prepend_domain=subdomain, staff=RoleSettings(anonymize=True))
    got_teacher1 = AsmStaff.from_dn(teacher1_dn, settings).as_csv_line()
    expected_teacher1 = [t1_name, t1_name, teacher1.name, "", "-", "", teacher1.name, school1]
    assert got_teacher1 == expected_teacher1, (
        f"CSV line for teacher1 anonymized,\nexp: {expected_teacher1!r}\ngot: {got_teacher1!r}"
    )

    first_name_anon = uts.random_name()
    settings = Settings(
        email_prepend_domain=subdomain,
        staff=RoleSettings(
            anonymize=True,
            anonymize_values={**DEFAULT_ANONYMIZE_VALUES, "first_name": first_name_anon},
        ),
    )
    got_teacher1 = AsmStaff.from_dn(teacher1_dn, settings).as_csv_line()
    expected_teacher1 = [
        t1_name,
        t1_name,
        first_name_anon,
        "",
        "-",
        "",
        teacher1.name,
        school1,
    ]
    assert got_teacher1 == expected_teacher1, (
        f"CSV line with static first_name for teacher1 anonymized,\nexp: {expected_teacher1!r}\ngot: {got_teacher1!r}."
    )
