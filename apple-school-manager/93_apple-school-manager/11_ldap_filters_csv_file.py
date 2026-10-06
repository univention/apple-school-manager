#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test ldap filter for student and staff csv generation
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [48346]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import logging
import tempfile
from collections.abc import Callable, Iterator
from typing import Any, NamedTuple

import pytest
import univention.testing.strings as uts
from ldap.filter import filter_format
from univention.admin import uexceptions
from univention.admin.uldap import access
from univention.asm.config import Settings, parse_config
from univention.asm.csv.csv_file import AsmRostersCsvFile, AsmStaffCsvFile, AsmStudentsCsvFile
from univention.asm.models.staff import get_filtered_staff
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

log = logging.getLogger(__name__)

CSV_FILE_CLASSES = {"staff": AsmStaffCsvFile, "student": AsmStudentsCsvFile}


class Users(NamedTuple):
    school: str
    by_role: dict[str, tuple[str, str]]


def build_settings(
    school: str,
    defaults: dict[str, Any],
    school_entry: dict[str, Any] | None = None,
) -> Settings:
    with tempfile.NamedTemporaryFile("w") as password_file:
        password_file.write("secret")
        password_file.flush()
        config = {
            "accounts": {"test": {"username": "test", "password_file": password_file.name}},
            "defaults": defaults,
            "schools": {school: {"account": "test", **(school_entry or {})}},
        }
        return parse_config(config)[0].settings


@pytest.fixture(autouse=True)
def _clear_staff_cache(caplog: pytest.LogCaptureFixture) -> Iterator[None]:
    caplog.set_level(logging.DEBUG, logger="univention.asm")
    get_filtered_staff.cache_clear()
    yield
    get_filtered_staff.cache_clear()


@pytest.fixture
def school(create_ous: Callable[..., list[tuple[str, str]]]) -> str:
    [(name, _dn)] = create_ous(1)
    return name


@pytest.fixture
def users(schoolenv: UCSTestSchool, lo: access, school: str) -> Users:
    school_class1 = f"{school}-{uts.random_username()}"
    teacher1_name, _teacher1_dn = schoolenv.create_teacher(school, classes=school_class1)
    teacher2_name, _teacher2_dn = schoolenv.create_teacher_and_staff(school, classes=school_class1)
    student1_name, _student1_dn = schoolenv.create_student(school, classes=school_class1)
    student2_name, _student2_dn = schoolenv.create_student(school, classes=school_class1)
    log.info(
        "*** school_class1=%r",
        lo.search(
            filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class1,)),
            attr=["memberUid"],
        ),
    )
    # users to be ignored by filters:
    schoolenv.create_teacher(school)
    schoolenv.create_teacher_and_staff(school)
    schoolenv.create_student(school)
    return Users(
        school=school,
        by_role={
            "staff": (teacher1_name, teacher2_name),
            "student": (student1_name, student2_name),
        },
    )


@pytest.mark.parametrize("role", ["staff", "student"])
def test_invalid_filter_raises(school: str, role: str) -> None:
    settings = build_settings(school, {role: {"ldap_filter": "NONSENSE"}})
    with pytest.raises(uexceptions.valueInvalidSyntax):
        list(CSV_FILE_CLASSES[role]("", settings).find_and_create_objects())
    if role == "student":
        get_filtered_staff.cache_clear()
        with pytest.raises(uexceptions.valueInvalidSyntax):
            list(AsmRostersCsvFile("", settings).find_and_create_objects())


@pytest.mark.parametrize("role", ["staff", "student"])
@pytest.mark.parametrize("school_specific", [False, True], ids=["global", "school_specific"])
def test_filter_selects_user(users: Users, role: str, *, school_specific: bool) -> None:
    user1, user2 = users.by_role[role]
    expected_user = user2 if school_specific else user1
    settings = build_settings(
        users.school,
        {role: {"ldap_filter": f"uid={user1}"}},
        {role: {"ldap_filter": f"uid={user2}"}} if school_specific else None,
    )
    user_objs: list[Any] = list(CSV_FILE_CLASSES[role]("", settings).find_and_create_objects())
    assert len(user_objs) == 1, f"Not exactly 1 user object found: {user_objs}"
    assert expected_user == user_objs[0].sis_username, (
        f"The filter selects '{expected_user}', which was not found in {user_objs}"
    )

    if role == "student":
        get_filtered_staff.cache_clear()
        roster_objs = list(AsmRostersCsvFile("", settings).find_and_create_objects())
        assert len(roster_objs) == 1, f"Not exactly 1 roster object found: {roster_objs}"
        assert roster_objs[0].student_id == user_objs[0].person_id
