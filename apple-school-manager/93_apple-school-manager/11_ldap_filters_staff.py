#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: test ldap filter for AsmStaff class method get_filtered_staff
## tags: [apptest]
## exposure: dangerous
## packages:
##   - univention-apple-school-manager-connector
## bugs: [52920]

import logging

import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
from ldap.filter import filter_format
from univention.admin import uexceptions

from univention.asm.models.staff import AsmStaff
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
		filter_type = "staff"
		teacher1_name, teacher1_dn = self.schoolenv.create_teacher(
			school1, classes=school_class1
		)
		teacher2_name, teacher2_dn = self.schoolenv.create_teacher_and_staff(
			school1, classes=school_class1
		)
		teacher1_id = get_person_id_by_dn(teacher1_dn, "staff")
		teacher2_id = get_person_id_by_dn(teacher2_dn, "staff")

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

		self.log.info("Test if global filter works for AsmClass")
		ucr_v = "asm/ldap_filter/staff=NONSENSE"
		set_and_update_ucr(ucr_v)
		try:
			_ = AsmStaff.get_filtered_staff(self.lo, self.log, school1)
			self.fail(
				"We expect an valueInvalidSyntax exception with an invalid filter for filter "
				"type 'staff'"
			)
		except uexceptions.valueInvalidSyntax:
			self.log.info("*** OK: expected exception was raised (AsmClass).")

		ucr_v = "asm/ldap_filter/{}=uid={}".format(filter_type, teacher1_name)
		set_and_update_ucr(ucr_v)
		teachers = AsmStaff.get_filtered_staff(self.lo, self.log, school1)
		filtered_teacher_ids = [get_person_id_by_dn(teacher.dn, "staff") for teacher in teachers]
		assert teacher1_id in filtered_teacher_ids
		assert len(filtered_teacher_ids) == 1, "Not exactly 1 staff object found: {}".format(filtered_teacher_ids)
		self.log.info(
			"*** OK: found expected user %r for filter_type=%r with global filter.",
			teacher1_name,
			filter_type,
		)

		ucr_v = "asm/ldap_filter/{}=(!(uid={}))".format(filter_type, teacher1_name)
		set_and_update_ucr(ucr_v)
		teachers = AsmStaff.get_filtered_staff(self.lo, self.log, school1)
		filtered_teacher_ids = [get_person_id_by_dn(teacher.dn, "staff") for teacher in teachers]
		assert teacher1_id not in filtered_teacher_ids
		assert teacher2_id in filtered_teacher_ids
		self.log.info(
			"*** OK: did not find user %r for filter_type=%r with global filter.",
			teacher1_name,
			filter_type,
		)

		self.log.info("Test if overriding with school specific filter works")
		ucr_v = "asm/ldap_filter/{}/{}=uid={}".format(
			filter_type, school1, teacher1_name
		)
		set_and_update_ucr(ucr_v)
		teachers = AsmStaff.get_filtered_staff(self.lo, self.log, school1)
		filtered_teacher_ids = [get_person_id_by_dn(teacher.dn, "staff") for teacher in teachers]
		assert teacher1_id in filtered_teacher_ids
		assert len(filtered_teacher_ids) == 1, "Not exactly 1 staff object found: {}".format(filtered_teacher_ids)
		self.log.info(
			"*** OK: found expected user %r for filter_type=%r with school specific filter.",
			teacher1_name,
			filter_type,
		)

		ucr_v = "asm/ldap_filter/{}/{}=(!(uid={}))".format(
			filter_type, school1, teacher1_name
		)
		set_and_update_ucr(ucr_v)
		teachers = AsmStaff.get_filtered_staff(self.lo, self.log, school1)
		filtered_teacher_ids = [get_person_id_by_dn(teacher.dn, "staff") for teacher in teachers]
		assert teacher1_id not in filtered_teacher_ids
		assert teacher2_id in filtered_teacher_ids
		self.log.info(
			"*** OK: did not find user %r for filter_type=%r with school specific filter.",
			teacher1_name,
			filter_type,
		)


if __name__ == "__main__":
	with ucr_test.UCSTestConfigRegistry():
		Test().run()
