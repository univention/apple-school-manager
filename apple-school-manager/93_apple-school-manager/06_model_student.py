#!/usr/share/ucs-test/runner python3
## desc: test student model/CSV generation
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import univention.testing.strings as uts
from ucsschool.lib.models.user import Student
from univention.asm.config import DEFAULT_ANONYMIZE_VALUES, Settings, StudentSettings
from univention.asm.models.student import AsmStudent
from univention.asm.utils import get_person_id
from univention.testing import utils
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


class Test(ImportTestbase):  # type: ignore[misc]
    ou_C = None

    def test(self) -> None:
        subdomain = uts.random_name()
        settings = Settings(email_prepend_domain=subdomain, student=StudentSettings(anonymize=False))

        assert StudentSettings().password_policy == 4, (
            f"Default password_policy is {StudentSettings().password_policy!r}, expected 4."
        )

        school1 = self.ou_A.name
        school2 = self.ou_B.name

        student1_name, student1_dn = self.schoolenv.create_student(school1)
        email_local = uts.random_name()
        email = f"{email_local}@{self.maildomain}"
        email_sub = f"{email_local}@{subdomain}.{self.maildomain}"
        student2_name, student2_dn = self.schoolenv.create_student(
            school2,
            schools=[school1, school2],
            mailaddress=email,
        )
        self.log.info("Created student1: %r (%s)", student1_name, student1_dn)
        self.log.info("Created student2: %r (%s)", student2_name, student2_dn)

        # check if this system has a schema that supports a middle name
        student1 = Student.from_dn(student1_dn, None, self.lo)
        student_udm_obj = student1.get_udm_object(self.lo)
        for attr in ("middleName", "initials", "oxMiddleName"):
            if attr in student_udm_obj:
                middle_name = uts.random_name(length=5)
                self.log.info("*** Adding middle name to student1: %r...", middle_name)
                student_udm_obj[attr] = middle_name
                student_udm_obj.modify()
                utils.verify_ldap_object(student1_dn, {attr: [middle_name]})
                # reload object just to be safe
                student1 = Student.from_dn(student1_dn, None, self.lo)
                break
        else:
            self.log.info("*** No LDAP schema for middle name attribute found.")
            middle_name = ""

        student2 = Student.from_dn(student2_dn, None, self.lo)

        s1_id_attr, s1_lo = get_person_id(student1_dn, "entryUUID", [])
        s1_name = s1_lo[s1_id_attr][0]
        s2_id_attr, s2_lo = get_person_id(student2_dn, "entryUUID", [])
        s2_name = s2_lo[s2_id_attr][0]

        or_student1 = AsmStudent.from_dn(student1_dn, settings)
        got_student1 = or_student1.as_csv_line()
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
        if got_student1 == expected_student1:
            self.log.info("OK: student1 CSV line is as expected.")
        else:
            self.fail(
                f"CSV line for student1,\nexp: {expected_student1!r}\ngot: {got_student1!r}.",
            )

        settings = Settings(
            email_prepend_domain=subdomain,
            student=StudentSettings(anonymize=False, grade_level_attribute="sn"),
        )
        or_student1 = AsmStudent.from_dn(student1_dn, settings)
        got_student1 = or_student1.as_csv_line()
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
        if got_student1 == expected_student1:
            self.log.info("OK: student1 CSV line is as expected.")
        else:
            self.fail(
                f"CSV line for student1,\nexp: {expected_student1!r}\ngot: {got_student1!r}.",
            )

        settings = Settings(
            email_prepend_domain=subdomain,
            student=StudentSettings(anonymize=False, grade_level_attribute="sn", password_policy=None),
        )
        or_student2 = AsmStudent.from_dn(student2_dn, settings)
        got_student2 = or_student2.as_csv_line()
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
        if got_student2 == expected_student2:
            self.log.info("OK: student2 CSV line is as expected.")
        else:
            self.fail(
                f"CSV line for student2,\nexp: {expected_student2!r}\ngot: {got_student2!r}.",
            )

        settings = Settings(
            email_prepend_domain=subdomain,
            student=StudentSettings(anonymize=True, grade_level_attribute="sn", password_policy=6),
        )
        or_student1 = AsmStudent.from_dn(student1_dn, settings)
        got_student1 = or_student1.as_csv_line()
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
        if got_student1 == expected_student1:
            self.log.info("OK: student1 anonymized CSV line is as expected.")
        else:
            self.fail(
                f"CSV line for student1 anonymized,\nexp: {expected_student1!r}\ngot: {got_student1!r}.",
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
        or_student1 = AsmStudent.from_dn(student1_dn, settings)
        got_student1 = or_student1.as_csv_line()
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
        if got_student1 == expected_student1:
            self.log.info("OK: student1 anonymized CSV line with static last_name is as expected.")
        else:
            self.fail(
                f"CSV line with static last_name for student1 anonymized,\nexp: {expected_student1!r}\ngot: {got_student1!r}.",
            )


if __name__ == "__main__":
    Test().run()
