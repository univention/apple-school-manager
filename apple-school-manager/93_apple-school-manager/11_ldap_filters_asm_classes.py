#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test ldap filter staff inside school classes
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
from univention.asm.models.classes import AsmClass
from univention.asm.models.staff import get_filtered_staff
from univention.asm.utils import get_person_id
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

log = logging.getLogger(__name__)


class SchoolClassWithStaff(NamedTuple):
    school: str
    dn: str
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
def school_class(
    schoolenv: UCSTestSchool, lo: access, create_ous: Callable[..., list[tuple[str, str]]]
) -> SchoolClassWithStaff:
    [(school1, _dn)] = create_ous(1)
    school_class1 = f"{school1}-{uts.random_username()}"
    teacher1_name, teacher1_dn = schoolenv.create_teacher(school1, classes=school_class1)
    _teacher2_name, teacher2_dn = schoolenv.create_teacher_and_staff(school1, classes=school_class1)
    found = lo.search(
        filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class1,)),
        attr=["memberUid"],
    )
    log.info("*** school_class1=%r", found)
    # users to be ignored by filters:
    schoolenv.create_teacher(school1)
    schoolenv.create_teacher_and_staff(school1)
    schoolenv.create_student(school1)
    return SchoolClassWithStaff(
        school=school1,
        dn=found[0][0],
        teacher1_name=teacher1_name,
        teacher1_id=get_person_id_by_dn(teacher1_dn),
        teacher2_id=get_person_id_by_dn(teacher2_dn),
    )


def class_settings(
    school_class: SchoolClassWithStaff, default_filter: str, school_filter: str | None
) -> Settings:
    return build_settings(
        school_class.school,
        {"staff": {"ldap_filter": default_filter.format(teacher1=school_class.teacher1_name)}},
        {"staff": {"ldap_filter": school_filter.format(teacher1=school_class.teacher1_name)}}
        if school_filter
        else None,
    )


def test_invalid_filter_raises(school_class: SchoolClassWithStaff) -> None:
    settings = build_settings(school_class.school, {"staff": {"ldap_filter": "NONSENSE"}})
    with pytest.raises(uexceptions.valueInvalidSyntax):
        AsmClass.from_dn(school_class.dn, settings)


@pytest.mark.parametrize(
    ("default_filter", "school_filter"),
    [
        ("uid={teacher1}", None),
        ("(!(uid={teacher1}))", "uid={teacher1}"),
    ],
    ids=["global", "school_specific"],
)
def test_filter_includes_teacher(
    school_class: SchoolClassWithStaff, default_filter: str, school_filter: str | None
) -> None:
    settings = class_settings(school_class, default_filter, school_filter)
    asm_class = AsmClass.from_dn(school_class.dn, settings)
    assert asm_class.instructor_id == school_class.teacher1_id
    assert not (asm_class.instructor_id_2 or asm_class.instructor_id_3), (
        f"Not exactly 1 staff object found: {asm_class}"
    )


@pytest.mark.parametrize(
    ("default_filter", "school_filter"),
    [
        ("(!(uid={teacher1}))", None),
        ("(!(uid={teacher1}))", "(!(uid={teacher1}))"),
    ],
    ids=["global", "school_specific"],
)
def test_filter_excludes_teacher(
    school_class: SchoolClassWithStaff, default_filter: str, school_filter: str | None
) -> None:
    settings = class_settings(school_class, default_filter, school_filter)
    asm_class = AsmClass.from_dn(school_class.dn, settings)
    assert asm_class.instructor_id != school_class.teacher1_id
    assert asm_class.instructor_id == school_class.teacher2_id
