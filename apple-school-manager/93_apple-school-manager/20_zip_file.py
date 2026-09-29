#!/usr/share/ucs-test/runner python3
## desc: test ZIP generation
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622]  # noqa: ERA001

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import csv
import os
import tempfile
import zipfile
from operator import itemgetter

import univention.testing.strings as uts
from ldap.filter import filter_format
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.school import School
from univention.asm.config import RoleSettings, SchoolSettings, Settings, StudentSettings
from univention.asm.csv.zip_file import AsmZipFile
from univention.asm.utils import get_person_id
from univention.testing import utils
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


class Test(ImportTestbase):  # type: ignore[misc]
    use_ou_cache = False  # use only uncached OUs to be certain no previous test left any object

    def _get_user_attr(self, dn: str) -> dict[str, str]:
        user = self.lo.get(dn)
        middle_name = (
            user.get("middleName", [""])[0]
            or user.get("initials", [""])[0]
            or user.get("oxMiddleName", [""])[0]
        )
        return {
            "first": user.get("givenName", [b""])[0].decode(),
            "middle": middle_name,
            "last": user.get("sn", [b""])[0].decode(),
            "email": user.get("mailPrimaryAddress", [""])[0],
        }

    def test(self) -> None:
        school1 = self.ou_A.name
        school2 = self.ou_B.name
        school3 = self.ou_C.name

        schools = [school1, school2]
        settings = Settings(
            student=StudentSettings(anonymize=False),
            staff=RoleSettings(anonymize=False),
            schools={school: SchoolSettings() for school in schools},
            other_schools=None,
        )
        school_class1 = f"{school1}-{uts.random_username()}"
        school_class2 = f"{school2}-{uts.random_username()}"
        school_class3 = f"{school3}-{uts.random_username()}"
        school_class4 = f"{school1}-{uts.random_username()}"

        school2_display_name = uts.random_string()
        self.log.info("Setting display_name of school2 (%s) to %r.", school2, school2_display_name)
        sc2 = School.from_dn(self.ou_B.dn, self.ou_B.name, self.lo)
        sc2.display_name = school2_display_name
        sc2.modify(self.lo)
        utils.verify_ldap_object(self.ou_B.dn, {"displayName": [school2_display_name]})

        self.log.info("*** Creating users...")

        self.schoolenv.create_staff(school1)
        self.schoolenv.create_staff(school2)
        self.schoolenv.create_staff(school3)

        teacher1_name, teacher1_dn = self.schoolenv.create_teacher(
            school1,
            schools=schools,
            classes=f"{school_class1},{school_class2}",
        )
        teacher2_name, teacher2_dn = self.schoolenv.create_teacher(
            school1,
            schools=schools,
            classes=f"{school_class1},{school_class2},{school_class4}",
        )
        teacher3_name, teacher3_dn = self.schoolenv.create_teacher(
            school2,
            schools=schools,
            classes=f"{school_class1},{school_class2}",
        )
        teacher4_name, teacher4_dn = self.schoolenv.create_teacher(
            school2,
            schools=schools,
            classes=f"{school_class1},{school_class2},{school_class4}",
        )
        teacher5_name, teacher5_dn = self.schoolenv.create_teacher_and_staff(
            school2,
            classes=school_class2,
        )
        teacher6_name, teacher6_dn = self.schoolenv.create_teacher_and_staff(
            school2,
            schools=[school2, school3],
            classes=f"{school_class2},{school_class3}",
        )
        teacher7_name, _teacher7_dn = self.schoolenv.create_teacher_and_staff(
            school3,
            classes=school_class3,
        )

        student1_name, student1_dn = self.schoolenv.create_student(school1, classes=school_class1)
        student2_name, student2_dn = self.schoolenv.create_student(
            school1,
            schools=schools,
            classes=f"{school_class1},{school_class2}",
        )
        student3_name, student3_dn = self.schoolenv.create_student(
            school1,
            schools=schools,
            classes=f"{school_class1},{school_class2},{school_class4}",
        )
        student4_name, student4_dn = self.schoolenv.create_student(
            school2,
            schools=schools,
            classes=f"{school_class1},{school_class2}",
        )
        student5_name, student5_dn = self.schoolenv.create_student(
            school2,
            schools=schools,
            classes=f"{school_class1},{school_class2}",
        )
        student6_name, student6_dn = self.schoolenv.create_student(school1, classes=school_class1)
        student7_name, student7_dn = self.schoolenv.create_student(school2, classes=school_class2)
        student8_name, _student8_dn = self.schoolenv.create_student(school3, classes=school_class3)

        t1_id_attr, t1_lo = get_person_id(teacher1_dn, "entryUUID", [])
        t1_name = t1_lo[t1_id_attr][0]
        t2_id_attr, t2_lo = get_person_id(teacher2_dn, "entryUUID", [])
        t2_name = t2_lo[t2_id_attr][0]
        t3_id_attr, t3_lo = get_person_id(teacher3_dn, "entryUUID", [])
        t3_name = t3_lo[t3_id_attr][0]
        t4_id_attr, t4_lo = get_person_id(teacher4_dn, "entryUUID", [])
        t4_name = t4_lo[t4_id_attr][0]
        t5_id_attr, t5_lo = get_person_id(teacher5_dn, "entryUUID", [])
        t5_name = t5_lo[t5_id_attr][0]
        t6_id_attr, t6_lo = get_person_id(teacher6_dn, "entryUUID", [])
        t6_name = t6_lo[t6_id_attr][0]
        s1_id_attr, s1_lo = get_person_id(student1_dn, "entryUUID", [])
        s1_name = s1_lo[s1_id_attr][0]
        s2_id_attr, s2_lo = get_person_id(student2_dn, "entryUUID", [])
        s2_name = s2_lo[s2_id_attr][0]
        s3_id_attr, s3_lo = get_person_id(student3_dn, "entryUUID", [])
        s3_name = s3_lo[s3_id_attr][0]
        s4_id_attr, s4_lo = get_person_id(student4_dn, "entryUUID", [])
        s4_name = s4_lo[s4_id_attr][0]
        s5_id_attr, s5_lo = get_person_id(student5_dn, "entryUUID", [])
        s5_name = s5_lo[s5_id_attr][0]
        s6_id_attr, s6_lo = get_person_id(student6_dn, "entryUUID", [])
        s6_name = s6_lo[s6_id_attr][0]
        s7_id_attr, s7_lo = get_person_id(student7_dn, "entryUUID", [])
        s7_name = s7_lo[s7_id_attr][0]

        self.log.info("Created a staff in each OU.")

        self.log.info(f"school1={school1!r} school2={school2!r} school3={school3!r} ...")
        self.log.info(f"school_class1={school_class1!r} school_class2={school_class2!r} ...")
        self.log.info(f"school_class3={school_class3!r} school_class4={school_class4!r} ...")
        self.log.info(
            "teacher1: %r school: %r schools: %r classes: %r",
            teacher1_name,
            school1,
            schools,
            f"{school_class1},{school_class2}",
        )
        self.log.info(
            "teacher2: %r school: %r schools: %r classes: %r",
            teacher2_name,
            school1,
            schools,
            f"{school_class1},{school_class2},{school_class4}",
        )
        self.log.info(
            "teacher3: %r school: %r schools: %r classes: %r",
            teacher3_name,
            school2,
            schools,
            f"{school_class1},{school_class2}",
        )
        self.log.info(
            "teacher4: %r school: %r schools: %r classes: %r",
            teacher4_name,
            school2,
            schools,
            f"{school_class1},{school_class2},{school_class4}",
        )
        self.log.info(
            "teacher5: %r school: %r schools: %r classes: %r",
            teacher5_name,
            school2,
            [school2],
            school_class2,
        )
        self.log.info(
            "teacher6: %r school: %r schools: %r classes: %r",
            teacher6_name,
            school2,
            [school2, school3],
            f"{school_class2},{school_class3}",
        )
        self.log.info(
            "teacher7: %r school: %r schools: %r classes: %r",
            teacher7_name,
            school3,
            [school3],
            school_class3,
        )

        self.log.info(
            "student1: %r school: %r schools: %r classes: %r",
            student1_name,
            school1,
            [school1],
            school_class1,
        )
        self.log.info(
            "student2: %r school: %r schools: %r classes: %r",
            student2_name,
            school1,
            schools,
            f"{school_class1},{school_class2}",
        )
        self.log.info(
            "student3: %r school: %r schools: %r classes: %r",
            student3_name,
            school1,
            schools,
            f"{school_class1},{school_class2},{school_class4}",
        )
        self.log.info(
            "student4: %r school: %r schools: %r classes: %r",
            student4_name,
            school1,
            schools,
            f"{school_class1},{school_class2}",
        )
        self.log.info(
            "student5: %r school: %r schools: %r classes: %r",
            student5_name,
            school1,
            schools,
            f"{school_class1},{school_class2}",
        )
        self.log.info(
            "student6: %r school: %r schools: %r classes: %r",
            student6_name,
            school1,
            [school1],
            school_class1,
        )
        self.log.info(
            "student7: %r school: %r schools: %r classes: %r",
            student7_name,
            school2,
            [school2],
            school_class2,
        )
        self.log.info(
            "student8: %r school: %r schools: %r classes: %r",
            student8_name,
            school3,
            [school3],
            school_class3,
        )

        self.log.info(
            "Created school_class1=%r",
            self.lo.search(
                filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class1,)),
                attr=["memberUid"],
            ),
        )
        self.log.info(
            "Created school_class2=%r",
            self.lo.search(
                filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class2,)),
                attr=["memberUid"],
            ),
        )
        self.log.info(
            "Created school_class3=%r",
            self.lo.search(
                filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class3,)),
                attr=["memberUid"],
            ),
        )
        self.log.info(
            "Created school_class4=%r",
            self.lo.search(
                filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class4,)),
                attr=["memberUid"],
            ),
        )

        self.log.info("Checking school classes...")
        filter_s = filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class1,))
        res = self.lo.searchDn(filter=filter_s)
        if len(res) != 1:
            self.fail(
                f"School class 1 not found: search with filter={filter_s!r} did not return 1 result:\n{res}",
            )
        school_class1_dn = res[0]
        utils.verify_ldap_object(
            school_class1_dn,
            {
                "memberUid": [
                    teacher1_name,
                    teacher2_name,
                    teacher3_name,
                    teacher4_name,
                    student1_name,
                    student2_name,
                    student3_name,
                    student4_name,
                    student5_name,
                    student6_name,
                ],
            },
        )
        filter_s = filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class2,))
        res = self.lo.searchDn(filter=filter_s)
        if len(res) != 1:
            self.fail(
                f"School class 2 not found: search with filter={filter_s!r} did not return 1 result:\n{res}",
            )
        school_class2_dn = res[0]
        school_class2_description = uts.random_string()
        self.log.info("*** Adding description to school_class2: %r...", school_class2_description)
        sc2 = SchoolClass.from_dn(school_class2_dn, school2, self.lo)
        sc2.description = school_class2_description
        sc2.modify(self.lo)
        utils.verify_ldap_object(
            school_class2_dn,
            {
                "memberUid": [
                    teacher1_name,
                    teacher2_name,
                    teacher3_name,
                    teacher4_name,
                    teacher5_name,
                    teacher6_name,
                    student2_name,
                    student3_name,
                    student4_name,
                    student5_name,
                    student7_name,
                ],
                "description": [school_class2_description],
            },
        )

        filter_s = filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class3,))
        res = self.lo.searchDn(filter=filter_s)
        if len(res) != 1:
            self.fail(
                f"School class 3 not found: search with filter={filter_s!r} did not return 1 result:\n{res}",
            )
        school_class3_dn = res[0]
        utils.verify_ldap_object(
            school_class3_dn,
            {"memberUid": [teacher6_name, teacher7_name, student8_name]},
        )
        filter_s = filter_format("(&(objectClass=univentionGroup)(cn=%s))", (school_class4,))
        res = self.lo.searchDn(filter=filter_s)
        if len(res) != 1:
            self.fail(
                f"School class 4 not found: search with filter={filter_s!r} did not return 1 result:\n{res}",
            )
        school_class4_dn = res[0]
        utils.verify_ldap_object(
            school_class4_dn,
            {"memberUid": [teacher2_name, teacher4_name, student3_name]},
        )
        self.log.info("OK: school class creation.")

        def check_classes(class_csv_file_name: str) -> None:
            with open(class_csv_file_name) as class_csv_file:  # open csv-file in text mode
                expected_school_classes = sorted(
                    [
                        [
                            school_class1,
                            "",
                            school_class1,
                            t1_name,
                            t2_name,
                            t3_name,
                            school1,
                            t4_name,
                            "",
                            "",
                        ],
                        [
                            school_class2,
                            "",
                            school_class2,
                            t1_name,
                            t2_name,
                            t3_name,
                            school2,
                            t4_name,
                            t5_name,
                            t6_name,
                        ],
                        # school3 is not in the whitelist, so school_class3 must not be returned
                        [
                            school_class4,
                            "",
                            school_class4,
                            t2_name,
                            t4_name,
                            "",
                            school1,
                            "",
                            "",
                            "",
                        ],
                    ],
                    key=itemgetter(0),
                )  # sort by 1. school name, 2. class name
                got_school_classes = list(csv.reader(class_csv_file))[1:]  # remove header line
                if got_school_classes == expected_school_classes:
                    self.log.info("OK: school_classes CSV file is as expected.")
                else:
                    self.fail(
                        "Expected CSV for school_classes: ------\n"
                        "{!r}\n"
                        "------- got school_classes: ------\n{!r}\n"
                        "------- CSV produced: ------\n{}".format(
                            expected_school_classes,
                            got_school_classes,
                            "\n".join(open(class_csv_file.name).read().split("\n")),
                        ),
                    )

        def check_courses(course_csv_file_name: str) -> None:
            with open(course_csv_file_name) as course_csv_file:  # open csv-file in text mode
                expected_courses = sorted(
                    [
                        [school_class1, school_class1, school_class1, school1],
                        [school_class2, school_class2, school_class2, school2],
                        # school3 is not in the whitelist, so school_class3 must not be returned
                        [school_class4, school_class4, school_class4, school1],
                    ],
                    key=itemgetter(0),
                )  # sort by 1. school name, 2. class name
                got_courses = list(csv.reader(course_csv_file))[1:]  # remove header line
                if got_courses == expected_courses:
                    self.log.info("OK: courses CSV file is as expected.")
                else:
                    self.fail(
                        "Expected CSV for courses: ------\n"
                        "{!r}\n"
                        "------- got courses: ------\n{!r}\n"
                        "------- CSV produced: ------\n{}".format(
                            expected_courses,
                            got_courses,
                            "\n".join(open(course_csv_file.name).read().split("\n")),
                        ),
                    )

        def check_location(location_csv_file_name: str) -> None:
            with open(location_csv_file_name) as location_csv_file:  # open csv-file in text mode
                expected_locations = sorted(
                    [
                        [school1, school1],
                        [school2, school2_display_name],
                        # school3 is not in the whitelist, so school3 must not be returned
                    ],
                    key=itemgetter(0),
                )  # sort by school name
                got_locations = list(csv.reader(location_csv_file))[1:]  # remove header line
                if got_locations == expected_locations:
                    self.log.info("OK: locations CSV file is as expected.")
                else:
                    self.fail(
                        "Expected CSV for locations: ------\n"
                        "{!r}\n"
                        "------- got locations: ------\n{!r}\n"
                        "------- CSV produced: ------\n{}".format(
                            expected_locations,
                            got_locations,
                            "\n".join(open(location_csv_file.name).read().split("\n")),
                        ),
                    )

        def check_roster(roster_csv_file_name: str) -> None:
            with open(roster_csv_file_name) as roster_csv_file:  # open csv-file in text mode
                roster = []
                for student_name in sorted(
                    (
                        (student1_name, s1_name),
                        (student2_name, s2_name),
                        (student3_name, s3_name),
                        (student4_name, s4_name),
                        (student5_name, s5_name),
                        (student6_name, s6_name),
                    ),
                    key=itemgetter(0),
                ):
                    roster.append(
                        (
                            (school_class1, student_name[0]),  # sort key
                            [f"{school_class1}-{student_name[1]}", school_class1, student_name[1]],
                        ),
                    )
                for student_name in sorted(
                    (
                        (student2_name, s2_name),
                        (student3_name, s3_name),
                        (student4_name, s4_name),
                        (student5_name, s5_name),
                        (student7_name, s7_name),
                    ),
                    key=itemgetter(0),
                ):
                    roster.append(
                        (
                            (school_class2, student_name[0]),  # sort key
                            [f"{school_class2}-{student_name[1]}", school_class2, student_name[1]],
                        ),
                    )
                # school3 is not in the whitelist, so school3 must not be returned
                roster.append(
                    (
                        (school_class4, student3_name),  # sort key
                        [f"{school_class4}-{s3_name}", school_class4, s3_name],
                    ),
                )
                roster.sort(
                    key=itemgetter(0),
                )  # sort by 1. school name, 2. class name, 3. student name
                expected_roster = list(map(itemgetter(1), roster))
                got_roster = list(csv.reader(roster_csv_file))[1:]  # remove header line
                if got_roster == expected_roster:
                    self.log.info("OK: roster CSV file is as expected.")
                else:
                    self.fail(
                        "Expected CSV for roster: ------\n"
                        "{!r}\n"
                        "------- got roster: ------\n{!r}\n"
                        "------- CSV produced: ------\n{}".format(
                            expected_roster,
                            got_roster,
                            "\n".join(open(roster_csv_file.name).read().split("\n")),
                        ),
                    )

        def check_staff(staff_csv_file_name: str) -> None:
            with open(staff_csv_file_name) as staff_csv_file:  # open csv-file in text mode
                expected_staff = []
                teachers = map(
                    itemgetter(1),
                    sorted(
                        [
                            (
                                (school1, teacher1_name),
                                (school1, teacher1_name, t1_name, teacher1_dn, school2),
                            ),
                            (
                                (school1, teacher2_name),
                                (school1, teacher2_name, t2_name, teacher2_dn, school2),
                            ),
                            (
                                (school2, teacher3_name),
                                (school2, teacher3_name, t3_name, teacher3_dn, school1),
                            ),
                            (
                                (school2, teacher4_name),
                                (school2, teacher4_name, t4_name, teacher4_dn, school1),
                            ),
                            (
                                (school2, teacher5_name),
                                (school2, teacher5_name, t5_name, teacher5_dn, ""),
                            ),
                            (
                                (school2, teacher6_name),
                                (school2, teacher6_name, t6_name, teacher6_dn, ""),
                            ),
                        ],
                        key=itemgetter(0),
                    ),
                )  # sorted by 1. school, 2. username
                # school3 is not in the whitelist, so school3 must not be returned
                for s1, t_name, t_id, t_dn, s2 in teachers:
                    atts = self._get_user_attr(t_dn)
                    expected_staff.append(
                        [
                            t_id,
                            t_id,
                            atts["first"],
                            atts["middle"],
                            atts["last"],
                            atts["email"],
                            t_name,
                            s1,
                            s2,
                        ],
                    )
                got_staff = list(csv.reader(staff_csv_file))[1:]  # remove header line
                if got_staff == expected_staff:
                    self.log.info("OK: staff CSV file is as expected.")
                else:
                    self.fail(
                        "Expected CSV for staff: ------\n"
                        "{!r}\n"
                        "------- got staff: ------\n{!r}\n"
                        "------- CSV produced: ------\n{}".format(
                            expected_staff,
                            got_staff,
                            "\n".join(open(staff_csv_file.name).read().split("\n")),
                        ),
                    )

        def check_student(student_csv_file_name: str) -> None:
            assert settings.student.password_policy == 4, (
                f"Default password_policy is {settings.student.password_policy!r}, expected 4."
            )

            with open(student_csv_file_name) as student_csv_file:  # open csv-file in text mode
                expected_students = []
                teachers = map(
                    itemgetter(1),
                    sorted(
                        [
                            (
                                (school1, student1_name),
                                (school1, student1_name, s1_name, student1_dn, ""),
                            ),
                            (
                                (school1, student2_name),
                                (school1, student2_name, s2_name, student2_dn, school2),
                            ),
                            (
                                (school1, student3_name),
                                (school1, student3_name, s3_name, student3_dn, school2),
                            ),
                            (
                                (school2, student4_name),
                                (school2, student4_name, s4_name, student4_dn, school1),
                            ),
                            (
                                (school2, student5_name),
                                (school2, student5_name, s5_name, student5_dn, school1),
                            ),
                            (
                                (school1, student6_name),
                                (school1, student6_name, s6_name, student6_dn, ""),
                            ),
                            (
                                (school2, student7_name),
                                (school2, student7_name, s7_name, student7_dn, ""),
                            ),
                        ],
                        key=itemgetter(0),
                    ),
                )  # sorted by 1. school, 2. username
                # school3 is not in the whitelist, so school3 must not be returned
                for s1, t_name, t_id, t_dn, s2 in teachers:
                    atts = self._get_user_attr(t_dn)
                    expected_students.append(
                        [
                            t_id,
                            t_id,
                            atts["first"],
                            atts["middle"],
                            atts["last"],
                            "",
                            atts["email"],
                            t_name,
                            "4",
                            s1,
                            s2,
                        ],
                    )
                got_students = list(csv.reader(student_csv_file))[1:]  # remove header line
                if got_students == expected_students:
                    self.log.info("OK: students CSV file is as expected.")
                else:
                    self.fail(
                        "Expected CSV for students: ------\n"
                        "{!r}\n"
                        "------- got students: ------\n{!r}\n"
                        "------- CSV produced: ------\n{}".format(
                            expected_students,
                            got_students,
                            "\n".join(open(student_csv_file.name).read().split("\n")),
                        ),
                    )

        with tempfile.NamedTemporaryFile() as zip_result_file:
            zip_path = AsmZipFile(zip_result_file.name, settings).write_zip()
            assert zip_path == zip_result_file.name
            tmp_dir = tempfile.mkdtemp()
            zf = zipfile.ZipFile(zip_path)
            zf.extractall(tmp_dir)
            extracted_csv_files = set(os.listdir(tmp_dir))
            expected_csv_files = {
                "classes.csv",
                "courses.csv",
                "locations.csv",
                "rosters.csv",
                "staff.csv",
                "students.csv",
            }
            assert extracted_csv_files == expected_csv_files

        check_classes(os.path.join(tmp_dir, "classes.csv"))
        check_courses(os.path.join(tmp_dir, "courses.csv"))
        check_location(os.path.join(tmp_dir, "locations.csv"))
        check_roster(os.path.join(tmp_dir, "rosters.csv"))
        check_staff(os.path.join(tmp_dir, "staff.csv"))
        check_student(os.path.join(tmp_dir, "students.csv"))


if __name__ == "__main__":
    Test().run()
