#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: test course model/CSV generation
## tags: [apptest]
## exposure: dangerous
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622]

from ldap.filter import filter_format
from ucsschool.lib.models.group import SchoolClass
from univention.config_registry import handler_unset, handler_set

import univention.testing.ucr as ucr_test
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.asm.models.course import AsmCourse
from univention.asm.utils import update_ucr
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase

def get_course_name(course_pattern, school, name):
	return course_pattern.format(ou=school, name=name)


class Test(ImportTestbase):
	ou_B = None
	ou_C = None

	def test(self):
		school_class1 = '{}-{}'.format(self.ou_A.name, uts.random_username())
		school_class2 = '{}-{}'.format(self.ou_A.name, uts.random_username())

		self.log.info('*** Creating a teacher with 2 school_classes: %r %r...', school_class1, school_class2)
		teacher1_name, teacher1_dn = self.schoolenv.create_teacher(
			self.ou_A.name, classes='{},{}'.format(school_class1, school_class2))
		work_group1_description = uts.random_name()
		work_group1_name, work_group1_dn = self.schoolenv.create_workgroup(
			self.ou_A.name, description=work_group1_description, users=[teacher1_dn])
		self.log.info('Created teacher1: %r (%s)', teacher1_name, teacher1_dn)
		self.log.info(
			'Created school_class1=%r',
			self.lo.search(filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class1,)), attr=['memberUid'])
		)
		self.log.info(
			'Created school_class2=%r',
			self.lo.search(filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class1,)), attr=['memberUid'])
		)
		self.log.info(
			'Created work_group1=%r',
			self.lo.search(filter_format('(&(objectClass=univentionGroup)(cn=%s))', (work_group1_name,)), attr=['memberUid'])
		)

		filter_s = filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class1,))
		res = self.lo.searchDn(filter=filter_s)
		if len(res) != 1:
			self.fail('School class 1 not found: search with filter={!r} did not return 1 result:\n{}'.format(
				filter_s, res))
		school_class1_dn = res[0]
		utils.verify_ldap_object(school_class1_dn, {'memberUid': [teacher1_name]})

		filter_s = filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class2,))
		res = self.lo.searchDn(filter=filter_s)
		if len(res) != 1:
			self.fail('School class 2 not found: search with filter={!r} did not return 1 result:\n{}'.format(
				filter_s, res))
		school_class2_dn = res[0]
		utils.verify_ldap_object(school_class2_dn, {'memberUid': [teacher1_name]})

		description = uts.random_string()
		self.log.info('*** Adding description to school_class2: %r...', description)
		sc2 = SchoolClass.from_dn(school_class2_dn, self.ou_A.name, self.lo)
		sc2.description = description
		sc2.modify(self.lo)
		utils.verify_ldap_object(school_class2_dn, {'memberUid': [teacher1_name], 'description': [description]})

		utils.verify_ldap_object(work_group1_dn, {'memberUid': [teacher1_name]})

		for course_pattern in ["{name}", "{ou}-{name}", "{name}-{random}-{ou}"]:
				course_pattern = course_pattern.replace("{random}", uts.random_string())
				handler_set(["asm/attributes/course-name-pattern={}".format(course_pattern)])
				update_ucr()

				course1 = AsmCourse.from_dn(school_class1_dn)
				got_course1 = course1.as_csv_line()
				school, school_class1_name = school_class1.split("-", 1)
				course_name = get_course_name(course_pattern, school, school_class1_name)

				expected_course1 = [school_class1, school_class1, course_name, self.ou_A.name]
				if got_course1 == expected_course1:
					self.log.info('OK: course1 CSV line is as expected.')
				else:
					self.fail('Expected CSV line for course1: {!r}, got: {!r}.'.format(expected_course1, got_course1))

				course2 = AsmCourse.from_dn(school_class2_dn)
				got_course2 = course2.as_csv_line()
				school, school_class2_name = school_class2.split("-", 1)
				course_name = get_course_name(course_pattern, school, school_class2_name)
				expected_course2 = [school_class2, school_class2, course_name, self.ou_A.name]
				if got_course2 == expected_course2:
					self.log.info('OK: course2 CSV line is as expected.')
				else:
					self.fail('Expected CSV line for course2: {!r}, got: {!r}.'.format(expected_course2, got_course2))

				workgroup1 = AsmCourse.from_dn(work_group1_dn)
				got_workgroup1 = workgroup1.as_csv_line()
				_work_group1_name = work_group1_name.split("-", 1)[1]
				course_name = get_course_name(course_pattern, self.ou_A.name, _work_group1_name)
				expected_workgroup1 = [work_group1_name, work_group1_name, course_name, self.ou_A.name]
				if got_workgroup1 == expected_workgroup1:
					self.log.info('OK: workgroup1 CSV line is as expected.')
				else:
					self.fail('Expected CSV line for workgroup1: {!r}, got: {!r}.'.format(expected_workgroup1, got_workgroup1))


if __name__ == '__main__':
	with ucr_test.UCSTestConfigRegistry():
		handler_unset([
			"asm/attributes/user/email/prepend_domain",
			"asm/attributes/classes/class_number_empty",
			"asm/attributes/staff/anonymize",
			"asm/attributes/student/anonymize",
		])
		Test().run()
