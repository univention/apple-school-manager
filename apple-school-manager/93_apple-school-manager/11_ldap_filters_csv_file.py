#!/usr/share/ucs-test/runner python3
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
from typing import Any

import univention.testing.strings as uts
from ldap.filter import filter_format
from univention.admin import uexceptions
from univention.asm.config import Settings, parse_config
from univention.asm.csv.csv_file import AsmRostersCsvFile, AsmStaffCsvFile, AsmStudentsCsvFile
from univention.asm.models.staff import get_filtered_staff
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


class Test(ImportTestbase):  # type: ignore[misc]
    def test(self) -> None:
        school1 = self.ou_A.name
        school_class1 = f"{school1}-{uts.random_username()}"
        teacher1_name, _teacher1_dn = self.schoolenv.create_teacher(
            school1,
            classes=school_class1,
        )
        teacher2_name, _teacher2_dn = self.schoolenv.create_teacher_and_staff(
            school1,
            classes=school_class1,
        )
        student1_name, _student1_dn = self.schoolenv.create_student(
            school1,
            classes=school_class1,
        )
        student2_name, _student2_dn = self.schoolenv.create_student(
            school1,
            classes=school_class1,
        )
        self.log.info(
            "*** school_class1=%r",
            self.lo.search(
                filter_format(
                    "(&(objectClass=univentionGroup)(cn=%s))",
                    (school_class1,),
                ),
                attr=["memberUid"],
            ),
        )
        # users to be ignored by filters:
        self.schoolenv.create_teacher(school1)
        self.schoolenv.create_teacher_and_staff(school1)
        self.schoolenv.create_student(school1)

        # capture asm logging
        asm_logger = logging.getLogger("univention.asm")
        asm_logger.setLevel(logging.DEBUG)
        for handler in self.log.handlers:
            asm_logger.addHandler(handler)

        #  For staff, students and roster
        for klass, user1, user2, role in (
            (AsmStaffCsvFile, teacher1_name, teacher2_name, "staff"),
            (AsmStudentsCsvFile, student1_name, student2_name, "student"),
        ):
            get_filtered_staff.cache_clear()
            self.log.info(
                "===> klass=%r user1=%r user2=%r role=%r",
                klass.__name__,
                user1,
                user2,
                role,
            )
            ldap_filter = "NONSENSE"
            settings = build_settings(school1, {role: {"ldap_filter": ldap_filter}})
            #  invalid filter raised exception
            # user:
            try:
                _ = list(klass("", settings).find_and_create_objects())
                self.fail(
                    "We expect an valueInvalidSyntax exception with an invalid filter for filter "
                    f"type '{role}'",
                )
            except uexceptions.valueInvalidSyntax:
                self.log.info(
                    "*** OK: expected exception was raised (%s).",
                    klass.__name__,
                )
            get_filtered_staff.cache_clear()
            # roster:
            if role == "student":
                try:
                    _ = list(AsmRostersCsvFile("", settings).find_and_create_objects())
                    self.fail(
                        "We expect an valueInvalidSyntax exception with an invalid filter for filter "
                        f"type '{role}'",
                    )
                except uexceptions.valueInvalidSyntax:
                    self.log.info(
                        "*** OK: expected exception was raised (%s).",
                        AsmRostersCsvFile.__name__,
                    )

            get_filtered_staff.cache_clear()
            #  global filter works
            # user:
            ldap_filter = f"uid={user1}"
            settings = build_settings(school1, {role: {"ldap_filter": ldap_filter}})
            user_objs: list[Any] = list(klass("", settings).find_and_create_objects())
            assert len(user_objs) == 1, f"Not exactly 1 user object found: {user_objs}"
            assert user1 == user_objs[0].sis_username, (
                f"The filter is: {ldap_filter}. '{user1}' was not found in {user_objs}"
            )
            self.log.info(
                "*** OK: found expected user %r for role=%r with global filter.",
                user1,
                role,
            )

            # roster:
            if role == "student":
                get_filtered_staff.cache_clear()
                roster_objs = list(AsmRostersCsvFile("", settings).find_and_create_objects())
                assert len(roster_objs) == 1, f"Not exactly 1 roster object found: {roster_objs}"
                assert roster_objs[0].student_id == user_objs[0].person_id
                self.log.info(
                    "*** OK: found expected user %r in roster for role=%r with global filter.",
                    user1,
                    role,
                )

            get_filtered_staff.cache_clear()
            self.log.info("Test if overriding with school specific filter works")
            # user:
            ldap_filter = f"uid={user2}"
            settings = build_settings(
                school1,
                {role: {"ldap_filter": f"uid={user1}"}},
                {role: {"ldap_filter": ldap_filter}},
            )
            user_objs = list(klass("", settings).find_and_create_objects())
            assert len(user_objs) == 1, f"Not exactly 1 user object found: {user_objs}"
            assert user2 == user_objs[0].sis_username
            self.log.info(
                "*** OK: found expected user %r for role=%r with school specific filter.",
                user2,
                role,
            )
            # roster:
            if role == "student":
                get_filtered_staff.cache_clear()
                roster_objs = list(AsmRostersCsvFile("", settings).find_and_create_objects())
                assert len(roster_objs) == 1, f"Not exactly 1 roster object found: {roster_objs}"
                assert roster_objs[0].student_id == user_objs[0].person_id
                self.log.info(
                    "*** OK: found expected user %r in roster for role=%r with global filter.",
                    user2,
                    role,
                )


if __name__ == "__main__":
    Test().run()
