#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test class model/CSV generation
## tags: [apptest]
## exposure: dangerous
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622, 48511]

import random
from ldap.filter import filter_format
from univention.config_registry import handler_unset
import univention.testing.ucr as ucr_test
import univention.testing.strings as uts
import univention.testing.utils as utils
from ucsschool.lib.models.group import SchoolClass
from ucsschool.lib.models.user import User
from univention.asm.models.classes import AsmClass
from univention.asm.models.staff import get_filtered_staff
from univention.asm.utils import get_person_id
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


class Test(ImportTestbase):
	ou_C = None

	def test(self):
		user_creation_fn = [self.schoolenv.create_staff, self.schoolenv.create_teacher, self.schoolenv.create_teacher_and_staff]
		random.shuffle(user_creation_fn)
		ous = [self.ou_A.name, self.ou_B.name]
		random.shuffle(ous)
		school1 = ous[0]
		school2 = ous[1]
		schools = [school1, school2]
		school_class1 = '{}-{}'.format(school1, uts.random_username())
		school_class2 = '{}-{}'.format(school2, uts.random_username())

		self.log.info('*** Creating users: 1x staff, 1x teacher 1x teacher+staff, 2x student...')
		self.log.info('*** school1={!r} school2={!r} ...'.format(school1, school2))
		self.log.info('*** school_class1={!r} school_class2={!r} ...'.format(school_class1, school_class2))
		staff1_name, staff1_dn = self.schoolenv.create_staff(random.choice(ous))
		teacher1_name, teacher1_dn = self.schoolenv.create_teacher(
			school1, schools=schools, classes='{},{}'.format(school_class1, school_class2))
		teacher2_name, teacher2_dn = self.schoolenv.create_teacher_and_staff(school1, classes=school_class1)
		teacher3_name, teacher3_dn = self.schoolenv.create_teacher_and_staff(school1, classes=school_class1)
		teacher4_name, teacher4_dn = self.schoolenv.create_teacher_and_staff(school1, classes=school_class1)
		teacher5_name, teacher5_dn = self.schoolenv.create_teacher_and_staff(school1, classes=school_class1)
		student1_name, student1_dn = self.schoolenv.create_student(school1, classes=school_class1)
		student2_name, student2_dn = self.schoolenv.create_student(school2, classes=school_class2)
		# "users" are created in the reverse order!?!?!?!
		t1_id_attr, t1_lo = get_person_id(teacher1_dn, 'staff', [])
		t1_name = t1_lo[t1_id_attr][0]
		t2_id_attr, t2_lo = get_person_id(teacher2_dn, 'staff', [])
		t2_name = t2_lo[t2_id_attr][0]
		t3_id_attr, t3_lo = get_person_id(teacher3_dn, 'staff', [])
		t3_name = t3_lo[t3_id_attr][0]
		t4_id_attr, t4_lo = get_person_id(teacher4_dn, 'staff', [])
		t4_name = t4_lo[t4_id_attr][0]
		t5_id_attr, t5_lo = get_person_id(teacher5_dn, 'staff', [])
		t5_name = t5_lo[t5_id_attr][0]
		work_group1_name, work_group1_dn = self.schoolenv.create_workgroup(
			school1, description='The description {}'.format(school1), users=[teacher2_dn, teacher1_dn, student1_dn])
		work_group2_name, work_group2_dn = self.schoolenv.create_workgroup(
			school2, description='The description {}'.format(school2), users=[student2_dn])

		self.log.info('Created staff1: %r (%s)', staff1_name, staff1_dn)
		self.log.info('Created teacher1: %r (%s, %s)', teacher1_name, teacher1_dn, t1_name)
		self.log.info('Created teacher2: %r (%s, %s)', teacher2_name, teacher2_dn, t2_name)
		self.log.info('Created teacher3: %r (%s, %s)', teacher3_name, teacher3_dn, t3_name)
		self.log.info('Created teacher4: %r (%s, %s)', teacher4_name, teacher4_dn, t4_name)
		self.log.info('Created teacher5: %r (%s, %s)', teacher5_name, teacher5_dn, t5_name)
		self.log.info('Created student1: %r (%s)', student1_name, student1_dn)
		self.log.info('Created student2: %r (%s)', student2_name, student2_dn)
		self.log.info(
			'Created school_class1=%r',
			self.lo.search(filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class1,)), attr=['memberUid'])
		)
		self.log.info(
			'Created school_class2=%r',
			self.lo.search(filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class2,)), attr=['memberUid'])
		)
		self.log.info(
			'Created work_group1=%r',
			self.lo.search(filter_format('(&(objectClass=univentionGroup)(cn=%s))', (work_group1_name,)), attr=['memberUid'])
		)
		self.log.info(
			'Created work_group2=%r',
			self.lo.search(filter_format('(&(objectClass=univentionGroup)(cn=%s))', (work_group2_name,)), attr=['memberUid'])
		)

		filter_s = filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class1,))
		res = self.lo.searchDn(filter=filter_s)
		if len(res) != 1:
			self.fail('School class 1 not found: search with filter={!r} did not return 1 result:\n{}'.format(
				filter_s, res))
		school_class1_dn = res[0]
		utils.verify_ldap_object(
			school_class1_dn,
			{'memberUid': [teacher1_name, teacher2_name, teacher3_name, teacher4_name, teacher5_name, student1_name]}
		)

		filter_s = filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class2,))
		res = self.lo.searchDn(filter=filter_s)
		if len(res) != 1:
			self.fail('School class 2 not found: search with filter={!r} did not return 1 result:\n{}'.format(
				filter_s, res))
		school_class2_dn = res[0]
		utils.verify_ldap_object(school_class2_dn, {'memberUid': [teacher1_name, student2_name]})

		utils.verify_ldap_object(work_group1_dn, {'memberUid': [student1_name, teacher1_name, teacher2_name]})
		utils.verify_ldap_object(work_group2_dn, {'memberUid': [student2_name]})

		or_class1 = AsmClass.from_dn(school_class1_dn)
		got_school_class1 = or_class1.as_csv_line()
		expected_school_class1 = [
			school_class1, '', school_class1, t1_name, t2_name, t3_name, school1,
			t4_name, t5_name
		]
		if got_school_class1 == expected_school_class1:
			self.log.info('OK: school_class1 CSV line is as expected.')
		else:
			self.fail('Expected CSV line for school_class1: {!r}, got: {!r}.'.format(expected_school_class1, got_school_class1))

		or_class2 = AsmClass.from_dn(school_class2_dn)
		got_school_class2 = or_class2.as_csv_line()
		expected_school_class2 = [school_class2, '', school_class2, t1_name, '', '', school2]
		if got_school_class2 == expected_school_class2:
			self.log.info('OK: school_class2 CSV line is as expected.')
		else:
			self.fail('Expected CSV line for school_class2: {!r}, got: {!r}.'.format(expected_school_class2, got_school_class2))

		or_wg1 = AsmClass.from_dn(work_group1_dn)
		got_wg1 = or_wg1.as_csv_line()
		expected_wg1 = (  # handle random user order
			[work_group1_name, '', work_group1_name, t1_name, t2_name, '', school1],
			[work_group1_name, '', work_group1_name, t2_name, t1_name, '', school1],
		)
		if got_wg1 in expected_wg1:
			self.log.info('OK: work_group1 CSV line is as expected.')
		else:
			self.fail('Expected CSV line for work_group1: {!r}, got: {!r}.'.format(expected_wg1, got_wg1))

		or_wg2 = AsmClass.from_dn(work_group2_dn)
		got_wg2 = or_wg2.as_csv_line()
		expected_wg2 = [work_group2_name, '', work_group2_name, '', '', '', school2]
		if got_wg2 == expected_wg2:
			self.log.info('OK: work_group2 CSV line is as expected.')
		else:
			self.fail('Expected CSV line for work_group2: {!r}, got: {!r}.'.format(expected_wg2, got_wg2))
		# Bug #48511: not more than 3+12=15 instructors per class
		# school_class1 has 5 teachers now. adding 11.
		# the CSV should only contain 3+12=15 instructors and ignore 1 teacher.
		new_teacher_dns = []
		for _i in range(11):
			teacher_name, teacher_dn = self.schoolenv.create_teacher_and_staff(school1, classes=school_class1)
			new_teacher_dns.append(teacher_dn)
			self.log.info('Added teacher %r to %r.', teacher_name, school_class1)
		self.log.info(
			'Members of %r (school_class1) now: %r',
			school_class1,
			self.lo.search(filter_format('(&(objectClass=univentionGroup)(cn=%s))', (school_class1,)), attr=['memberUid'])[0][1]['memberUid']
		)

		teacher_count = 0
		sc1 = SchoolClass.from_dn(school_class1_dn, school1, self.lo)
		for user_dn in sc1.users:
			user = User.from_dn(user_dn, school1, self.lo)
			if user.is_teacher(self.lo):
				teacher_count += 1
		self.log.info('Counted %d teachers in %r (school_class1).', teacher_count, school_class1)
		get_filtered_staff.cache_clear()
		or_class1 = AsmClass.from_dn(school_class1_dn)
		got_school_class1 = or_class1.as_csv_line()
		for t_dn in new_teacher_dns[:10]:  # <-- dropping last teacher!
			t_id_attr, t_lo = get_person_id(t_dn, 'staff', [])
			t_name = t_lo[t_id_attr][0]
			expected_school_class1.append(t_name)
		if got_school_class1 == expected_school_class1:
			self.log.info('OK: school_class1 CSV line is as expected.')
		else:
			self.fail('Expected CSV line for school_class1: {!r}, got: {!r}.'.format(expected_school_class1, got_school_class1))


if __name__ == '__main__':
	with ucr_test.UCSTestConfigRegistry():
		handler_unset([
			"asm/attributes/user/email/prepend_domain",
			"asm/attributes/classes/class_number_empty",
			"asm/attributes/staff/anonymize",
			"asm/attributes/student/anonymize",
		])
		Test().run()
