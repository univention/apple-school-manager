# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Classes that produce ASM CSV files.

See https://support.apple.com/en-us/HT207029

Data in CSV files is always sorted by 1) school and 2) user/class name.
"""

import json
import logging
import os
from collections.abc import Iterable, Iterator
from operator import attrgetter
from typing import Any, cast

from ucsschool.importer.writer.csv_writer import CsvWriter
from ucsschool.importer.writer.result_exporter import ResultExporter
from ucsschool.lib.models.group import SchoolClass, WorkGroup
from ucsschool.lib.models.school import School
from ucsschool.lib.models.user import Student, Teacher

from univention.admin import uexceptions
from univention.asm.config import Settings
from univention.asm.models.base import AsmModel
from univention.asm.models.classes import AsmClass
from univention.asm.models.course import AsmCourse
from univention.asm.models.location import AsmLocation
from univention.asm.models.roster import AsmRoster
from univention.asm.models.staff import AsmStaff, get_filtered_staff
from univention.asm.models.student import AsmStudent
from univention.asm.utils import get_ldap_connection, is_central_replica

__all__ = (
    "AsmClassCsvFile",
    "AsmCoursesCsvFile",
    "AsmLocationsCsvFile",
    "AsmRostersCsvFile",
    "AsmStaffCsvFile",
    "AsmStudentsCsvFile",
    "create_csv_files",
)


class _AsmCsvWriter(ResultExporter):  # type: ignore[misc]
    """CSV file writer."""

    def __init__(self, header: Iterable[str], *args: Any, **kwargs: Any) -> None:
        self.header = header
        super().__init__(*args, **kwargs)

    def get_header(self) -> Iterable[str]:
        """
        Data for an optional header (line) before the main data.

        :return: object that can be used by the writer to create a header
        """
        return self.header

    def get_iter(self, objs: Iterable[AsmModel]) -> Iterable[AsmModel]:
        """
        Iterator over relevant objects.

        :param objs: list of AsmModel objects
        :return: iterator for AsmModel objects
        :rtype: Iterator
        """
        return objs

    def get_writer(self) -> CsvWriter:
        """
        Object that will write the data to disk in the desired format.

        :return: an object of a BaseWriter subclass
        :rtype: BaseWriter
        """
        return CsvWriter(field_names=self.get_header())

    def serialize(self, obj: AsmModel) -> dict[str, str]:
        """
        Make a dict of attr_name->strings from an object delivered by the
        iterator from get_iter().

        :param AsmModel obj: object to serialize
        :return: attr_name->strings that will be used to write the output file
        :rtype: dict
        """
        return obj.as_dict()


class AsmCsvFile:
    """Base class for all ASM CSV file generator classes."""

    header: list[str] = []
    asm_model_class: type[AsmModel] | None = None
    ucs_classes: list[SchoolClass | WorkGroup] = []
    lo = None

    def __init__(self, file_path: str, settings: Settings | None = None) -> None:
        """
        :param str file_path: file path to write CSV to
        :param settings: settings of the Apple School Manager account, only
                schools that the account receives are considered. All schools
                with the default settings if None.
        """
        self.file_path = file_path
        self.settings = settings or Settings()
        self.obj: list[AsmModel] = []
        self.logger = logging.getLogger(__name__)
        if not self.lo:
            self.__class__.lo, _po = get_ldap_connection()
        self.limbo_ou = self._get_limbo_ou()

    def find_and_create_objects(self) -> Iterator[AsmModel]:
        """
        Find LDAP objects and return created AsmModel objects.

        :return list of AsmModel objects
        :rtype: list(AsmModel)
        """
        if not self.asm_model_class:
            raise NotImplementedError

        schools = self.get_schools()
        for school in schools:
            ucs_objs = []
            for ucs_class in self.ucs_classes:
                ucs_objs.extend(ucs_class.get_all(self.lo, school.name))
            if ucs_objs and hasattr(ucs_objs[0], "name"):
                ucs_objs.sort(key=attrgetter("name"))
            for ucs_obj in ucs_objs:
                yield self.asm_model_class.from_dn(ucs_obj.dn, self.settings)

    def get_schools(self) -> Iterable[School]:
        """
        Get the School objects that the account receives.

        :return list of School objects
        :rtype: list(School)
        """
        schools = [
            s
            for s in School.get_all(self.lo, filter_local=not is_central_replica())
            if s.name != self.limbo_ou
        ]
        schools = [s for s in schools if self.settings.includes(s.name)]
        return sorted(schools, key=attrgetter("name"))

    def write_csv(self, objs: Iterable[AsmModel] | None = None) -> None:
        """
        Write CSV to `self.file_path`.

        :param objs: optional list of AsmModel objects, if not set `self.objs` will be used
        :type objs: list(AsmModel) or None
        """
        objs = objs or self.obj or self.find_and_create_objects()
        # walk through list (iterator really) and find longest header, because it's needed as first line
        res = []
        for obj in objs:
            res.append(obj)
            if len(obj.header) > len(self.header):
                self.header = obj.header
        orcw = _AsmCsvWriter(self.header)
        self.logger.info("Writing %d objects to %s...", len(res), os.path.basename(self.file_path))
        orcw.dump(res, self.file_path)

    def _get_limbo_ou(self) -> str:
        """
        Get the "limbo_ou", in case we have a "Single source database, partial
        import user import" scenario.

        :return: name or limbo OU or empty string
        :rtype: str
        """
        # Not using the importer code to get the import configuration object,
        # because that would trigger the configuration checks, and the import
        # might not be configured properly.

        school_names = [s.name for s in School.get_all(self.lo, filter_local=not is_central_replica())]
        config_files = [
            "/usr/share/ucs-school-import/configs/global_defaults.json",
            "/var/lib/ucs-school-import/configs/global.json",
            "/usr/share/ucs-school-import/configs/user_import_defaults.json",
            "/var/lib/ucs-school-import/configs/user_import.json",
            "/usr/share/ucs-school-import/configs/user_import_sisopi.json",
        ] + [f"/var/lib/ucs-school-import/configs/{ou}.json" for ou in school_names]
        config_files = [cf for cf in config_files if os.path.exists(cf)]
        config_files.reverse()  # search from most specific (OU) to most general (defaults)
        for config_file in config_files:
            with open(config_file, "rb") as fp:
                config = json.load(fp)
                try:
                    limbo_ou: str = config["limbo_ou"]
                except KeyError:
                    limbo_ou = ""
        return limbo_ou

    def get_staff(self, school: School) -> Iterable[Teacher]:
        return get_filtered_staff(
            self.lo,
            self.logger,
            school.name,
            self.settings.school(school.name).staff_ldap_filter,
        )

    def get_students(self, school: School) -> Iterable[Student]:
        specific_ldap_filter = self.settings.school(school.name).student_ldap_filter
        try:
            return [
                student
                for student in Student.get_all(self.lo, school.name, filter_str=specific_ldap_filter)
                if not student.is_exam_student(self.lo)
            ]
        except uexceptions.valueInvalidSyntax:
            self.logger.exception(f"Invalid LDAP-filter for students: {specific_ldap_filter!r}")
            raise
        except Exception as exc:
            self.logger.exception("other exc: %s", exc)
            raise


class AsmClassCsvFile(AsmCsvFile):
    """CSV file generator for the `classes` file."""

    header = AsmClass.header
    asm_model_class = AsmClass
    ucs_classes = [SchoolClass, WorkGroup]

    def find_and_create_objects(self) -> Iterator[AsmClass]:
        """
        Find LDAP objects and return created AsmModel objects.

        :return list of AsmModel objects
        :rtype: list(AsmClass)
        """
        return cast("Iterator[AsmClass]", super().find_and_create_objects())


class AsmCoursesCsvFile(AsmCsvFile):
    """CSV file generator for the `courses` file."""

    header = AsmCourse.header
    asm_model_class = AsmCourse
    ucs_classes = [SchoolClass, WorkGroup]

    def find_and_create_objects(self) -> Iterator[AsmCourse]:
        """
        Find LDAP objects and return created AsmModel objects.

        :return list of AsmModel objects
        :rtype: list(AsmCourse)
        """
        return cast("Iterator[AsmCourse]", super().find_and_create_objects())


class AsmLocationsCsvFile(AsmCsvFile):
    """CSV file generator for the `locations` file."""

    header = AsmLocation.header

    def find_and_create_objects(self) -> Iterator[AsmLocation]:
        """
        Find LDAP objects and return created AsmModel objects.

        :return list of AsmModel objects
        :rtype: list(AsmLocation)
        """
        schools = self.get_schools()
        for school in schools:
            yield AsmLocation.from_dn(school.dn)


class AsmRostersCsvFile(AsmCsvFile):
    """CSV file generator for the `rosters` file."""

    header = AsmRoster.header

    def find_and_create_objects(self) -> Iterator[AsmRoster]:
        """
        Find LDAP objects and return created AsmModel objects.

        :return list of AsmModel objects
        :rtype: list(AsmRoster)
        """
        for school in self.get_schools():
            student_dns = {student.dn for student in self.get_students(school)}
            for ucs_obj in sorted(
                SchoolClass.get_all(self.lo, school.name) + WorkGroup.get_all(self.lo, school.name),
                key=attrgetter("name"),
            ):
                for user_dn in sorted(ucs_obj.users):
                    if user_dn in student_dns:
                        yield AsmRoster.from_dn(ucs_obj.dn, user_dn, self.settings)


class AsmStaffCsvFile(AsmCsvFile):
    """CSV file generator for the `staff` file."""

    header = AsmStaff.header

    def find_and_create_objects(self) -> Iterator[AsmStaff]:
        """
        Find LDAP objects and return created AsmModel objects.

        :return list of AsmModel objects
        :rtype: list(AsmStaff)
        """
        staff_members = set()
        for school in self.get_schools():
            for teacher in self.get_staff(school):
                t_schools = [teacher.school, *sorted(s for s in teacher.schools if s != teacher.school)]
                t_schools = [s for s in t_schools if self.settings.includes(s)]
                staff_members.add((t_schools[0], teacher.name, teacher.dn))
        dns = [dn for school, name, dn in sorted(staff_members)]  # sorted by 1. school, 2. username
        for dn in dns:
            yield AsmStaff.from_dn(dn, self.settings)


class AsmStudentsCsvFile(AsmCsvFile):
    """CSV file generator for the `students` file."""

    header = AsmStudent.header

    def find_and_create_objects(self) -> Iterator[AsmStudent]:
        """
        Find LDAP objects and return created AsmModel objects.

        :return list of AsmModel objects
        :rtype: list(AsmStudent)
        """
        students = set()
        for school in self.get_schools():
            for student in self.get_students(school):
                s_schools = [student.school, *sorted(s for s in student.schools if s != student.school)]
                s_schools = [s for s in s_schools if self.settings.includes(s)]
                students.add((s_schools[0], student.name, student.dn))
        dns = [dn for school, name, dn in sorted(students)]  # sorted by 1. school, 2. username
        for dn in dns:
            yield AsmStudent.from_dn(dn, self.settings)


csv_file_generators = {
    "classes.csv": AsmClassCsvFile,
    "courses.csv": AsmCoursesCsvFile,
    "locations.csv": AsmLocationsCsvFile,
    "rosters.csv": AsmRostersCsvFile,
    "staff.csv": AsmStaffCsvFile,
    "students.csv": AsmStudentsCsvFile,
}


def create_csv_files(target_directory: str, settings: Settings | None = None) -> Iterable[str]:
    """
    Create CSV files in `target_directory`. Directory must either not exist or
    be empty.

    :param str target_directory: path to a directory in which to create the
            CSV files
    :param settings: settings of the Apple School Manager account, only
            schools that the account receives are considered. All schools with
            the default settings if None.
    :return: list of files created
    :rtype: list(str)
    :raises ValueError: if `target_directory` exists and is not a directory or
            empty
    """
    logger = logging.getLogger(__name__)
    if os.path.exists(target_directory) and not os.path.isdir(target_directory):
        msg = f"Is not a directory: {target_directory!r}."
        raise ValueError(msg)
    if os.path.isdir(target_directory):
        if os.listdir(target_directory):
            msg = f"Directory {target_directory!r} is not empty."
            raise ValueError(msg)
    else:
        os.mkdir(target_directory, 0o600)

    settings = settings or Settings()
    schools = sorted(settings.schools)
    if settings.other_schools is not None:
        schools.append("all other schools" if schools else "all schools")
    logger.info("Creating CSV files for %s...", ", ".join(schools))
    results = []
    for filename, cls in csv_file_generators.items():
        path = os.path.join(target_directory, filename)
        results.append(path)
        cls(path, settings).write_csv()
    logger.info("Finished creating CSV files.")
    return results
