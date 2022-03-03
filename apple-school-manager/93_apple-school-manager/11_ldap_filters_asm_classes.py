#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test ldap filter staff inside school classes
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

from univention.asm.models.classes import AsmClass
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

		get_filtered_staff.cache_clear()
		self.log.info("Test if global filter works for AsmClass")
		ucr_v = "asm/ldap_filter/staff=NONSENSE"
		set_and_update_ucr(ucr_v)
		try:
			_ = AsmClass.from_dn(school_class_dn)
			self.fail(
				"We expect an valueInvalidSyntax exception with an invalid filter for filter "
				"type 'staff'"
			)
		except uexceptions.valueInvalidSyntax:
			self.log.info("*** OK: expected exception was raised (AsmClass).")

		get_filtered_staff.cache_clear()
		ucr_v = "asm/ldap_filter/{}=uid={}".format(filter_type, teacher1_name)
		set_and_update_ucr(ucr_v)
		asm_class = AsmClass.from_dn(school_class_dn)
		assert asm_class.instructor_id == teacher1_id
		assert not (
			asm_class.instructor_id_2 or asm_class.instructor_id_3
		), "Not exactly 1 staff object found: {}".format(asm_class)
		self.log.info(
			"*** OK: found expected user %r for filter_type=%r with global filter.",
			teacher1_name,
			filter_type,
		)

		get_filtered_staff.cache_clear()
		ucr_v = "asm/ldap_filter/{}=(!(uid={}))".format(filter_type, teacher1_name)
		set_and_update_ucr(ucr_v)
		asm_class = AsmClass.from_dn(school_class_dn)
		assert asm_class.instructor_id != teacher1_id
		assert asm_class.instructor_id == teacher2_id
		self.log.info(
			"*** OK: did not find user %r for filter_type=%r with global filter.",
			teacher1_name,
			filter_type,
		)

		get_filtered_staff.cache_clear()
		self.log.info("Test if overriding with school specific filter works")
		ucr_v = "asm/ldap_filter/{}/{}=uid={}".format(
			filter_type, school1, teacher1_name
		)
		set_and_update_ucr(ucr_v)
		asm_class = AsmClass.from_dn(school_class_dn)
		assert asm_class.instructor_id == teacher1_id
		assert not (
			asm_class.instructor_id_2 or asm_class.instructor_id_3
		), "Not exactly 1 staff object found: {}".format(asm_class)
		self.log.info(
			"*** OK: found expected user %r for filter_type=%r with school specific filter.",
			teacher1_name,
			filter_type,
		)

		get_filtered_staff.cache_clear()
		ucr_v = "asm/ldap_filter/{}/{}=(!(uid={}))".format(
			filter_type, school1, teacher1_name
		)
		set_and_update_ucr(ucr_v)
		asm_class = AsmClass.from_dn(school_class_dn)
		assert asm_class.instructor_id != teacher1_id
		assert asm_class.instructor_id == teacher2_id
		self.log.info(
			"*** OK: did not find user %r for filter_type=%r with school specific filter.",
			teacher1_name,
			filter_type,
		)


if __name__ == "__main__":
	with ucr_test.UCSTestConfigRegistry():
		Test().run()
