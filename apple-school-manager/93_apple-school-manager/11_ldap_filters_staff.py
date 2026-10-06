#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test ldap filter for AsmStaff function get_filtered_staff
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [52920]  # noqa: ERA001

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
from univention.asm.models.staff import get_filtered_staff
from univention.asm.utils import get_person_id
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

log = logging.getLogger(__name__)


class Staff(NamedTuple):
    school: str
    teacher1_name: str
    teacher1_id: str
    teacher2_id: str


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


def get_person_id_by_dn(dn: str) -> str:
    id_attr, t1_lo = get_person_id(dn, "entryUUID", [])
    person_id: str = t1_lo[id_attr][0]
    return person_id


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
def staff(schoolenv: UCSTestSchool, lo: access, school: str) -> Staff:
    school_class1 = f"{school}-{uts.random_username()}"
    teacher1_name, teacher1_dn = schoolenv.create_teacher(school, classes=school_class1)
    _teacher2_name, teacher2_dn = schoolenv.create_teacher_and_staff(school, classes=school_class1)
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
    return Staff(
        school=school,
        teacher1_name=teacher1_name,
        teacher1_id=get_person_id_by_dn(teacher1_dn),
        teacher2_id=get_person_id_by_dn(teacher2_dn),
    )


def staff_settings(staff: Staff, default_filter: str, school_filter: str | None) -> Settings:
    return build_settings(
        staff.school,
        {"staff": {"ldap_filter": default_filter.format(teacher1=staff.teacher1_name)}},
        {"staff": {"ldap_filter": school_filter.format(teacher1=staff.teacher1_name)}}
        if school_filter
        else None,
    )


def filtered_staff_ids(lo: access, school: str, settings: Settings) -> list[str]:
    teachers = get_filtered_staff(lo, log, school, settings.school(school).staff_ldap_filter)
    return [get_person_id_by_dn(teacher.dn) for teacher in teachers]


def test_invalid_filter_raises(lo: access, school: str) -> None:
    settings = build_settings(school, {"staff": {"ldap_filter": "NONSENSE"}})
    with pytest.raises(uexceptions.valueInvalidSyntax):
        get_filtered_staff(lo, log, school, settings.school(school).staff_ldap_filter)


@pytest.mark.parametrize(
    ("default_filter", "school_filter"),
    [
        ("uid={teacher1}", None),
        ("(!(uid={teacher1}))", "uid={teacher1}"),
    ],
    ids=["global", "school_specific"],
)
def test_filter_includes_teacher(
    lo: access, staff: Staff, default_filter: str, school_filter: str | None
) -> None:
    settings = staff_settings(staff, default_filter, school_filter)
    filtered_teacher_ids = filtered_staff_ids(lo, staff.school, settings)
    assert staff.teacher1_id in filtered_teacher_ids
    assert len(filtered_teacher_ids) == 1, f"Not exactly 1 staff object found: {filtered_teacher_ids}"


@pytest.mark.parametrize(
    ("default_filter", "school_filter"),
    [
        ("(!(uid={teacher1}))", None),
        ("(!(uid={teacher1}))", "(!(uid={teacher1}))"),
    ],
    ids=["global", "school_specific"],
)
def test_filter_excludes_teacher(
    lo: access, staff: Staff, default_filter: str, school_filter: str | None
) -> None:
    settings = staff_settings(staff, default_filter, school_filter)
    filtered_teacher_ids = filtered_staff_ids(lo, staff.school, settings)
    assert staff.teacher1_id not in filtered_teacher_ids
    assert staff.teacher2_id in filtered_teacher_ids
