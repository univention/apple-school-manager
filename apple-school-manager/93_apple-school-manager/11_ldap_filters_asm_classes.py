#!/usr/share/ucs-test/runner python3
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
from typing import Any

import univention.testing.strings as uts
from ldap.filter import filter_format
from univention.admin import uexceptions
from univention.asm.config import Settings, parse_config
from univention.asm.models.classes import AsmClass
from univention.asm.models.staff import get_filtered_staff
from univention.asm.utils import get_person_id
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


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
    return t1_lo[id_attr][0]


class Test(ImportTestbase):  # type: ignore[misc]
    def test(self) -> None:
        school1 = self.ou_A.name
        school_class1 = f"{school1}-{uts.random_username()}"
        filter_type = "staff"
        teacher1_name, teacher1_dn = self.schoolenv.create_teacher(
            school1,
            classes=school_class1,
        )
        _teacher2_name, teacher2_dn = self.schoolenv.create_teacher_and_staff(
            school1,
            classes=school_class1,
        )
        teacher1_id = get_person_id_by_dn(teacher1_dn)
        teacher2_id = get_person_id_by_dn(teacher2_dn)

        school_class = self.lo.search(
            filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class1,)),
            attr=["memberUid"],
        )
        school_class_dn = school_class[0][0]
        self.log.info(
            "*** school_class1=%r",
            school_class,
        )
        # users to be ignored by filters:
        self.schoolenv.create_teacher(school1)
        self.schoolenv.create_teacher_and_staff(school1)
        self.schoolenv.create_student(school1)

        asm_logger = logging.getLogger("univention.asm")
        asm_logger.setLevel(logging.DEBUG)
        for handler in self.log.handlers:
            asm_logger.addHandler(handler)

        get_filtered_staff.cache_clear()
        self.log.info("Test if global filter works for AsmClass")
        ldap_filter = "NONSENSE"
        settings = build_settings(school1, {"staff": {"ldap_filter": ldap_filter}})
        try:
            _ = AsmClass.from_dn(school_class_dn, settings)
            self.fail(
                "We expect an valueInvalidSyntax exception with an invalid filter for filter "
                "type 'staff'",
            )
        except uexceptions.valueInvalidSyntax:
            self.log.info("*** OK: expected exception was raised (AsmClass).")

        get_filtered_staff.cache_clear()
        ldap_filter = f"uid={teacher1_name}"
        settings = build_settings(school1, {"staff": {"ldap_filter": ldap_filter}})
        asm_class = AsmClass.from_dn(school_class_dn, settings)
        assert asm_class.instructor_id == teacher1_id
        assert not (asm_class.instructor_id_2 or asm_class.instructor_id_3), (
            f"Not exactly 1 staff object found: {asm_class}"
        )
        self.log.info(
            "*** OK: found expected user %r for filter_type=%r with global filter.",
            teacher1_name,
            filter_type,
        )

        get_filtered_staff.cache_clear()
        ldap_filter = f"(!(uid={teacher1_name}))"
        settings = build_settings(school1, {"staff": {"ldap_filter": ldap_filter}})
        asm_class = AsmClass.from_dn(school_class_dn, settings)
        assert asm_class.instructor_id != teacher1_id
        assert asm_class.instructor_id == teacher2_id
        self.log.info(
            "*** OK: did not find user %r for filter_type=%r with global filter.",
            teacher1_name,
            filter_type,
        )

        get_filtered_staff.cache_clear()
        self.log.info("Test if overriding with school specific filter works")
        ldap_filter = f"uid={teacher1_name}"
        settings = build_settings(
            school1,
            {"staff": {"ldap_filter": f"(!(uid={teacher1_name}))"}},
            {"staff": {"ldap_filter": ldap_filter}},
        )
        asm_class = AsmClass.from_dn(school_class_dn, settings)
        assert asm_class.instructor_id == teacher1_id
        assert not (asm_class.instructor_id_2 or asm_class.instructor_id_3), (
            f"Not exactly 1 staff object found: {asm_class}"
        )
        self.log.info(
            "*** OK: found expected user %r for filter_type=%r with school specific filter.",
            teacher1_name,
            filter_type,
        )

        get_filtered_staff.cache_clear()
        ldap_filter = f"(!(uid={teacher1_name}))"
        settings = build_settings(
            school1,
            {"staff": {"ldap_filter": f"(!(uid={teacher1_name}))"}},
            {"staff": {"ldap_filter": ldap_filter}},
        )
        asm_class = AsmClass.from_dn(school_class_dn, settings)
        assert asm_class.instructor_id != teacher1_id
        assert asm_class.instructor_id == teacher2_id
        self.log.info(
            "*** OK: did not find user %r for filter_type=%r with school specific filter.",
            teacher1_name,
            filter_type,
        )


if __name__ == "__main__":
    Test().run()
