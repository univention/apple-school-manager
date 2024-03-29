#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: test ldap filter for student and staff csv generation
## tags: [apptest]
## exposure: dangerous
## packages:
##   - univention-apple-school-manager-connector
## bugs: [48346]

import logging

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
from ldap.filter import filter_format
from univention.admin import uexceptions
from univention.asm.csv.csv_file import AsmRostersCsvFile, AsmStaffCsvFile, AsmStudentsCsvFile
from univention.asm.models.staff import get_filtered_staff
from univention.asm.utils import get_person_id, update_ucr
from univention.config_registry import handler_set
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


def set_and_update_ucr(ucr_v):  # type: (str) -> None
	handler_set([ucr_v])
	update_ucr()


def get_person_id_by_dn(dn, role):  # type: (str, str) -> str
	id_attr, t1_lo = get_person_id(dn, role, [])
	return t1_lo[id_attr][0]


class Test(ImportTestbase):
	def test(self):
		school1 = self.ou_A.name
		school_class1 = "{}-{}".format(school1, uts.random_username())
		teacher1_name, teacher1_dn = self.schoolenv.create_teacher(
			school1, classes=school_class1
		)
		teacher2_name, teacher2_dn = self.schoolenv.create_teacher_and_staff(
			school1, classes=school_class1
		)
		student1_name, student1_dn = self.schoolenv.create_student(
			school1, classes=school_class1
		)
		student2_name, student2_dn = self.schoolenv.create_student(
			school1, classes=school_class1
		)
		self.log.info(
			"*** school_class1=%r",
			self.lo.search(
				filter_format(
					"(&(objectClass=univentionGroup)(cn=%s))", (school_class1,)
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
		for klass, user1, user2, filter_type in [
			(AsmStaffCsvFile, teacher1_name, teacher2_name, "staff"),
			(AsmStudentsCsvFile, student1_name, student2_name, "students"),
		]:
			get_filtered_staff.cache_clear()
			self.log.info(
				"===> klass=%r user1=%r user2=%r filter_type=%r",
				klass.__name__,
				user1,
				user2,
				filter_type,
			)
			csv_class = klass("")
			ucr_v = "asm/ldap_filter/{}=NONSENSE".format(filter_type)
			set_and_update_ucr(ucr_v)
			#  invalid filter raised exception
			# user:
			try:
				_ = list(csv_class.find_and_create_objects())
				self.fail(
					"We expect an valueInvalidSyntax exception with an invalid filter for filter "
					"type '{}'".format(filter_type)
				)
			except uexceptions.valueInvalidSyntax:
				self.log.info(
					"*** OK: expected exception was raised (%s).",
					csv_class.__class__.__name__,
				)
			get_filtered_staff.cache_clear()
			# roster:
			if filter_type == "students":
				try:
					_ = list(AsmRostersCsvFile("").find_and_create_objects())
					self.fail(
						"We expect an valueInvalidSyntax exception with an invalid filter for filter "
						"type '{}'".format(filter_type)
					)
				except uexceptions.valueInvalidSyntax:
					self.log.info(
						"*** OK: expected exception was raised (%s).",
						AsmRostersCsvFile.__name__,
					)

			get_filtered_staff.cache_clear()
			#  global filter works
			# user:
			ucr_v = "asm/ldap_filter/{}=uid={}".format(filter_type, user1)
			set_and_update_ucr(ucr_v)
			user_objs = list(csv_class.find_and_create_objects())
			assert len(user_objs) == 1, "Not exactly 1 user object found: {}".format(
				user_objs
			)
			assert (
				user1 == user_objs[0].first_name
			), "The ucr filter is: {}. '{}' was not found in {}".format(
				ucr_v, user1, user_objs
			)
			self.log.info(
				"*** OK: found expected user %r for filter_type=%r with global filter.",
				user1,
				filter_type,
			)

			# roster:
			if filter_type == "students":
				get_filtered_staff.cache_clear()
				roster_objs = list(AsmRostersCsvFile("").find_and_create_objects())
				assert (
					len(roster_objs) == 1
				), "Not exactly 1 roster object found: {}".format(roster_objs)
				assert roster_objs[0].student_id == user_objs[0].person_id
				self.log.info(
					"*** OK: found expected user %r in roster for filter_type=%r with global filter.",
					user1,
					filter_type,
				)

			get_filtered_staff.cache_clear()
			self.log.info("Test if overriding with school specific filter works")
			# user:
			ucr_v = "asm/ldap_filter/{}/{}=uid={}".format(
				filter_type, school1, user2
			)
			set_and_update_ucr(ucr_v)
			user_objs = list(csv_class.find_and_create_objects())
			assert len(user_objs) == 1, "Not exactly 1 user object found: {}".format(
				user_objs
			)
			assert user2 == user_objs[0].first_name
			self.log.info(
				"*** OK: found expected user %r for filter_type=%r with school specific filter.",
				user2,
				filter_type,
			)
			# roster:
			if filter_type == "students":
				get_filtered_staff.cache_clear()
				roster_objs = list(AsmRostersCsvFile("").find_and_create_objects())
				assert (
					len(roster_objs) == 1
				), "Not exactly 1 roster object found: {}".format(roster_objs)
				assert roster_objs[0].student_id == user_objs[0].person_id
				self.log.info(
					"*** OK: found expected user %r in roster for filter_type=%r with global filter.",
					user2,
					filter_type,
				)


if __name__ == "__main__":
	with ucr_test.UCSTestConfigRegistry():
		Test().run()
