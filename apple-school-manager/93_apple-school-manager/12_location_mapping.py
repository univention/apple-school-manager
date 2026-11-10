#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test mapping schools to existing Apple School Manager locations
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import csv
from collections.abc import Callable
from pathlib import Path

import univention.testing.strings as uts
from univention.asm.config import SchoolSettings, Settings
from univention.asm.csv.csv_file import create_csv_files
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool


def read_csv(directory: Path, name: str) -> list[dict[str, str]]:
    with (directory / name).open(newline="") as fp:
        return list(csv.DictReader(fp))


def test_location_mapping_in_all_csv_files(
    schoolenv: UCSTestSchool,
    create_ous: Callable[..., list[tuple[str, str]]],
    tmp_path: Path,
) -> None:
    (school1, _), (school2, _) = create_ous(2, use_cache=False)
    location_id = uts.random_name()
    location_name = uts.random_string()
    school2_location_name = uts.random_string()
    settings = Settings(
        schools={
            school1: SchoolSettings(location_id=location_id, location_name=location_name),
            school2: SchoolSettings(location_name=school2_location_name),
        },
        other_schools=None,
    )
    class1 = f"{school1}-{uts.random_username()}"
    class2 = f"{school2}-{uts.random_username()}"
    teacher, _ = schoolenv.create_teacher(
        school1, schools=[school1, school2], classes=f"{class1},{class2}"
    )
    student1, _ = schoolenv.create_student(
        school1, schools=[school1, school2], classes=f"{class1},{class2}"
    )
    student2, _ = schoolenv.create_student(
        school2, schools=[school2, school1], classes=f"{class1},{class2}"
    )

    target = tmp_path / "csv"
    create_csv_files(str(target), settings)

    locations = {row["location_id"]: row["location_name"] for row in read_csv(target, "locations.csv")}
    assert locations == {location_id: location_name, school2: school2_location_name}

    for name in ("classes.csv", "courses.csv"):
        rows = read_csv(target, name)
        id_column = "class_id" if name == "classes.csv" else "course_id"
        assert {row[id_column]: row["location_id"] for row in rows} == {
            class1: location_id,
            class2: school2,
        }, name

    students = {row["sis_username"]: row for row in read_csv(target, "students.csv")}
    assert (students[student1]["location_id"], students[student1]["location_id_2"]) == (
        location_id,
        school2,
    )
    assert (students[student2]["location_id"], students[student2]["location_id_2"]) == (
        school2,
        location_id,
    )
    staff = {row["sis_username"]: row for row in read_csv(target, "staff.csv")}
    assert (staff[teacher]["location_id"], staff[teacher]["location_id_2"]) == (location_id, school2)


def test_shared_location_in_all_csv_files(
    schoolenv: UCSTestSchool,
    create_ous: Callable[..., list[tuple[str, str]]],
    tmp_path: Path,
) -> None:
    (school1, _), (school2, _) = sorted(create_ous(2, use_cache=False))
    location_id = uts.random_name()
    location_name = uts.random_string()
    settings = Settings(
        schools={
            school1: SchoolSettings(location_id=location_id),
            school2: SchoolSettings(location_id=location_id, location_name=location_name),
        },
        other_schools=None,
    )
    class1 = f"{school1}-{uts.random_username()}"
    class2 = f"{school2}-{uts.random_username()}"
    teacher, _ = schoolenv.create_teacher(
        school1, schools=[school1, school2], classes=f"{class1},{class2}"
    )
    student, _ = schoolenv.create_student(
        school2, schools=[school2, school1], classes=f"{class1},{class2}"
    )

    target = tmp_path / "csv"
    create_csv_files(str(target), settings)

    locations = [(row["location_id"], row["location_name"]) for row in read_csv(target, "locations.csv")]
    assert locations == [(location_id, location_name)]

    for name in ("classes.csv", "courses.csv"):
        rows = read_csv(target, name)
        id_column = "class_id" if name == "classes.csv" else "course_id"
        assert {row[id_column]: row["location_id"] for row in rows} == {
            class1: location_id,
            class2: location_id,
        }, name

    students = {row["sis_username"]: row for row in read_csv(target, "students.csv")}
    assert (students[student]["location_id"], students[student].get("location_id_2", "")) == (
        location_id,
        "",
    )
    staff = {row["sis_username"]: row for row in read_csv(target, "staff.csv")}
    assert (staff[teacher]["location_id"], staff[teacher].get("location_id_2", "")) == (location_id, "")
