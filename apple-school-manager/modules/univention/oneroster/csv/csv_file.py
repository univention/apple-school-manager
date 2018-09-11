# -*- coding: utf-8 -*-
#
# Copyright 2018 Univention GmbH
#
# http://www.univention.de/
#
# All rights reserved.
#
# The source code of this program is made available
# under the terms of the GNU Affero General Public License version 3
# (GNU AGPL V3) as published by the Free Software Foundation.
#
# Binary versions of this program provided by Univention to you as
# well as other copyrighted, protected or trademarked materials like
# Logos, graphics, fonts, specific documentations and configurations,
# cryptographic keys etc. are subject to a license agreement between
# you and Univention and not subject to the GNU AGPL V3.
#
# In the case you use this program under the terms of the GNU AGPL V3,
# the program is provided in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License with the Debian GNU/Linux or Univention distribution in file
# /usr/share/common-licenses/AGPL-3; if not, see
# <http://www.gnu.org/licenses/>.

"""
Univention Apple School Manager Connector

Classes the produce OneRoster CSV files.

See https://support.apple.com/en-us/HT207029

Data in CSV files is always sorted by 1) school and 2) user/class name.
"""

from __future__ import absolute_import, unicode_literals
import os
import json
from operator import attrgetter
from ucsschool.lib.models import School, SchoolClass, Student, Teacher, TeachersAndStaff, User
from ucsschool.importer.writer.csv_writer import CsvWriter
from ucsschool.importer.writer.result_exporter import ResultExporter
from ucsschool.importer.utils.ldap_connection import get_readonly_connection
from univention.oneroster.models.classes import OneRosterClass
from univention.oneroster.models.course import OneRosterCourse
from univention.oneroster.models.location import OneRosterLocation
from univention.oneroster.models.roster import OneRosterRoster
from univention.oneroster.models.staff import OneRosterStaff
from univention.oneroster.models.student import OneRosterStudent

try:
	from typing import Any, AnyStr, Iterable, Iterator, Optional
	from univention.oneroster.models.base import OneRosterModel
except ImportError:
	pass


__all__ = (
	'OneRosterClassCsvFile', 'OneRosterCoursesCsvFile', 'OneRosterLocationsCsvFile', 'OneRosterRostersCsvFile',
	'OneRosterStaffCsvFile', 'OneRosterStudentsCsvFile', 'create_csv_files'
)


class _OneRosterCsvWriter(ResultExporter):
	"""
	CSV file writer.
	"""

	def __init__(self, header, *arg, **kwargs):  # type: (Iterable[AnyStr], *Any, **Any) -> None
		self.header = header
		super(_OneRosterCsvWriter, self).__init__(*arg, **kwargs)

	def get_header(self):  # type: () -> Iterable[AnyStr]
		"""
		Data for an optional header (line) before the main data.

		:return: object that can be used by the writer to create a header
		"""
		return self.header

	def get_iter(self, objs):  # type: (Iterable[OneRosterModel]) -> Iterable[OneRosterModel]
		"""
		Iterator over relevant objects.

		:param objs: list of OneRosterModel objects
		:return: iterator for OneRosterModel objects
		:rtype: Iterator
		"""
		return objs

	def get_writer(self):  # type: () -> CsvWriter
		"""
		Object that will write the data to disk in the desired format.

		:return: an object of a BaseWriter subclass
		:rtype: BaseWriter
		"""
		return CsvWriter(field_names=self.get_header())

	def serialize(self, obj):  # type: (OneRosterModel) -> Iterator[str]
		"""
		Make a dict of attr_name->strings from an object delivered by the
		iterator from get_iter().

		:param OneRosterModel obj: object to serialize
		:return: attr_name->strings that will be used to write the output file
		:rtype: dict
		"""
		return obj.as_dict()


class OneRosterCsvFile(object):
	"""Base class for all OneRoster CSV file generator classes."""

	header = ()
	ucs2oneroster_classes = (None, None)
	lo = None

	def __init__(self, file_path, ou_whitelist=None):  # type: (AnyStr, Optional[Iterable[AnyStr]]) -> None
		"""
		:param str file_path: file path to write CSV to
		:param ou_whitelist: list of schools/OUs that should be considered
			when looking for LDAP objects. No limit if empty or None.
		:type ou_whitelist: list(str) or None
		"""
		self.file_path = file_path
		self.ou_whitelist = ou_whitelist
		self.obj = []
		if not self.lo:
			self.__class__.lo, po = get_readonly_connection()
		self.limbo_ou = self._get_limbo_ou()

	def find_and_create_objects(self):  # type: () -> Iterator[OneRosterModel]
		"""
		Find LDAP objects and return created OneRoster objects.

		:return list of OneRoster objects
		:rtype: list(OneRosterModel)
		"""
		if all(self.ucs2oneroster_classes):
			ucs_class, or_class = self.ucs2oneroster_classes
		else:
			raise NotImplementedError()

		schools = self.get_schools()
		for school in schools:
			ucs_objs = ucs_class.get_all(self.lo, school.name)
			if ucs_objs and hasattr(ucs_objs[0], 'name'):
				ucs_objs.sort(key=attrgetter('name'))
			for ucs_obj in ucs_objs:
				yield or_class.from_dn(ucs_obj.dn)

	def get_schools(self):  # type: () -> Iterable[School]
		"""
		Get School objects, filtered by `self.ou_whitelist`.

		:return list of School objects
		:rtype: list(School)
		"""
		schools = [s for s in School.get_all(self.lo) if s.name != self.limbo_ou]
		if self.ou_whitelist:
			schools = [s for s in schools if s.name in self.ou_whitelist]
		return sorted(schools, key=attrgetter('name'))

	def write_csv(self, objs=None):  # type: (Optional[Iterable[OneRosterModel]]) -> None
		"""
		Write CSV to `self.file_path`.

		:param objs: optional list of OneRoster objects, if not set `self.objs` will be used
		:type objs: list(OneRosterModel) or None
		"""
		objs = objs or self.obj or self.find_and_create_objects()
		# walk through list (iterator really) and find longest header, because it's needed as first line
		res = []
		for obj in objs:
			res.append(obj)
			if len(obj.header) > len(self.header):
				self.header = obj.header
		orcw = _OneRosterCsvWriter(self.header)
		orcw.dump(res, self.file_path)

	def _get_limbo_ou(self):  # type: () -> AnyStr
		"""
		Get the "limbo_ou", in case we have a "Single source database, partial
		import user import" scenario.

		:return: name or limbo OU or empty string
		:rtype: str
		"""
		# Not using the importer code to get the import configuration object,
		# because that would trigger the configuration checks, and the import
		# might not be configured properly.

		school_names = [s.name for s in School.get_all(self.lo)]
		config_files = [
			'/usr/share/ucs-school-import/configs/global_defaults.json',
			'/var/lib/ucs-school-import/configs/global.json',
			'/usr/share/ucs-school-import/configs/user_import_defaults.json',
			'/var/lib/ucs-school-import/configs/user_import.json',
			'/usr/share/ucs-school-import/configs/user_import_sisopi.json'
		] + ['/var/lib/ucs-school-import/configs/{}.json'.format(ou) for ou in school_names]
		config_files = [cf for cf in config_files if os.path.exists(cf)]
		config_files.reverse()  # search from most specific (OU) to most general (defaults)
		for config_file in config_files:
			with open(config_file, 'rb') as fp:
				config = json.load(fp)
				try:
					return config['limbo_ou']
				except KeyError:
					pass
		return ''


class OneRosterClassCsvFile(OneRosterCsvFile):
	"""CSV file generator for the `classes` file."""

	header = OneRosterClass.header
	ucs2oneroster_classes = (SchoolClass, OneRosterClass)


class OneRosterCoursesCsvFile(OneRosterCsvFile):
	"""CSV file generator for the `courses` file."""

	header = OneRosterCourse.header
	ucs2oneroster_classes = (SchoolClass, OneRosterCourse)


class OneRosterLocationsCsvFile(OneRosterCsvFile):
	"""CSV file generator for the `locations` file."""

	header = OneRosterLocation.header

	def find_and_create_objects(self):  # type: () -> Iterator[OneRosterLocation]
		"""
		Find LDAP objects and return created OneRoster objects.

		:return list of OneRoster objects
		:rtype: list(OneRosterLocation)
		"""
		schools = self.get_schools()
		for school in schools:
			yield OneRosterLocation.from_dn(school.dn)


class OneRosterRostersCsvFile(OneRosterCsvFile):
	"""CSV file generator for the `rosters` file."""

	header = OneRosterRoster.header

	def find_and_create_objects(self):  # type: () -> Iterator[OneRosterRoster]
		"""
		Find LDAP objects and return created OneRoster objects.

		:return list of OneRoster objects
		:rtype: list(OneRosterRoster)
		"""
		schools = self.get_schools()
		for school in schools:
			for school_class in sorted(SchoolClass.get_all(self.lo, school.name), key=attrgetter('name')):
				for user_dn in sorted(school_class.users):
					user = User.from_dn(user_dn, None, self.lo)
					if user.is_student(self.lo) and not user.is_exam_student(self.lo):
						yield OneRosterRoster.from_dn(school_class.dn, user_dn)


class OneRosterStaffCsvFile(OneRosterCsvFile):
	"""CSV file generator for the `staff` file."""

	header = OneRosterStaff.header

	def find_and_create_objects(self):  # type: () -> Iterator[OneRosterStaff]
		"""
		Find LDAP objects and return created OneRoster objects.

		:return list of OneRoster objects
		:rtype: list(OneRosterStaff)
		"""
		schools = self.get_schools()
		dns = set()
		for school in schools:
			for teacher in Teacher.get_all(self.lo, school.name) + TeachersAndStaff.get_all(self.lo, school.name):
				t_schools = [teacher.school] + sorted(s for s in teacher.schools if s != teacher.school)
				if self.ou_whitelist:
					t_schools = [s for s in t_schools if s in self.ou_whitelist]
				dns.add((t_schools[0], teacher.name, teacher.dn))
		dns = [dn for school, name, dn in sorted(dns)]  # sorted by 1. school, 2. username
		for dn in dns:
			yield OneRosterStaff.from_dn(dn, ou_whitelist=self.ou_whitelist)


class OneRosterStudentsCsvFile(OneRosterCsvFile):
	"""CSV file generator for the `students` file."""

	header = OneRosterStudent.header

	def find_and_create_objects(self):  # type: () -> Iterator[OneRosterStudent]
		"""
		Find LDAP objects and return created OneRoster objects.

		:return list of OneRoster objects
		:rtype: list(OneRosterStudent)
		"""
		schools = self.get_schools()
		dns = set()
		for school in schools:
			for student in Student.get_all(self.lo, school.name):
				s_schools = [student.school] + sorted(s for s in student.schools if s != student.school)
				if self.ou_whitelist:
					s_schools = [s for s in s_schools if s in self.ou_whitelist]
				dns.add((s_schools[0], student.name, student.dn))
		dns = [dn for school, name, dn in sorted(dns)]  # sorted by 1. school, 2. username
		for dn in dns:
			yield OneRosterStudent.from_dn(dn, ou_whitelist=self.ou_whitelist)


csv_file_generators = {
	'classes.csv': OneRosterClassCsvFile,
	'courses.csv': OneRosterCoursesCsvFile,
	'locations.csv': OneRosterLocationsCsvFile,
	'rosters.csv': OneRosterRostersCsvFile,
	'staff.csv': OneRosterStaffCsvFile,
	'students.csv': OneRosterStudentsCsvFile,
}


def create_csv_files(target_directory, ou_whitelist=None):
	# type: (AnyStr, Optional[Iterable[AnyStr]]) -> Iterable[AnyStr]
	"""
	Create CSV files in `target_directory`. Directory must either not exist or
	be empty.

	:param str target_directory: path to a directory in which to create the
		CSV files
	:param ou_whitelist: list of schools/OUs that should be considered when
		looking at ou-overlapping users. No limit if empty or None.
	:type ou_whitelist: list(str) or None
	:return: list of files created
	:rtype: list(str)
	:raises ValueError: if `target_directory` exists and is not a directory or
		empty
	"""
	if os.path.exists(target_directory) and not os.path.isdir(target_directory):
		raise ValueError('Is not a directory: {!r}.'.format(target_directory))
	if os.path.isdir(target_directory):
		if os.listdir(target_directory):
			raise ValueError('Directory {!r} is not empty.'.format(target_directory))
	else:
		os.mkdir(target_directory, 0o600)

	results = []
	for filename, cls in csv_file_generators.items():
		path = os.path.join(target_directory, filename)
		results.append(path)
		cls(path, ou_whitelist).write_csv()
	return results
