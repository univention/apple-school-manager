#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test student model/CSV generation
## tags: [apptest]
## exposure: dangerous
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622]

from ucsschool.lib.models.user import Student
from univention.config_registry import handler_set, handler_unset
import univention.testing.ucr as ucr_test
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.asm.models.student import AsmStudent
from univention.asm.utils import get_default_password_policy, get_person_id, update_ucr
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


class Test(ImportTestbase):
	ou_C = None

	def test(self):
		subdomain = uts.random_name()
		handler_set(['asm/attributes/user/email/prepend_domain={}'.format(subdomain)])

		assert get_default_password_policy() == '4', "Unset asm/attributes/student/password_policy is {!r}, expected '4'.".format(get_default_password_policy())

		school1 = self.ou_A.name
		school2 = self.ou_B.name

		student1_name, student1_dn = self.schoolenv.create_student(school1)
		email_local = uts.random_name()
		email = '{}@{}'.format(email_local, self.maildomain)
		email_sub = '{}@{}.{}'.format(email_local, subdomain, self.maildomain)
		student2_name, student2_dn = self.schoolenv.create_student(school2, schools=[school1, school2], mailaddress=email)
		self.log.info('Created student1: %r (%s)', student1_name, student1_dn)
		self.log.info('Created student2: %r (%s)', student2_name, student2_dn)

		# check if this system has a schema that supports a middle name
		student1 = Student.from_dn(student1_dn, None, self.lo)
		student_udm_obj = student1.get_udm_object(self.lo)
		for attr in ('middleName', 'initials', 'oxMiddleName'):
			if attr in student_udm_obj:
				middle_name = uts.random_name(length=5)
				self.log.info('*** Adding middle name to student1: %r...', middle_name)
				student_udm_obj[attr] = middle_name
				student_udm_obj.modify()
				utils.verify_ldap_object(student1_dn, {attr: [middle_name]})
				# reload object just to be safe
				student1 = Student.from_dn(student1_dn, None, self.lo)
				break
		else:
			self.log.info('*** No LDAP schema for middle name attribute found.')
			middle_name = ''

		student2 = Student.from_dn(student2_dn, None, self.lo)

		s1_id_attr, s1_lo = get_person_id(student1_dn, 'student', [])
		s1_name = s1_lo[s1_id_attr][0]
		s2_id_attr, s2_lo = get_person_id(student2_dn, 'student', [])
		s2_name = s2_lo[s2_id_attr][0]

		or_student1 = AsmStudent.from_dn(student1_dn)
		got_student1 = or_student1.as_csv_line()
		expected_student1 = [
			s1_name, s1_name, student1.firstname, middle_name, student1.lastname, '', '', student1_name, '4', school1
		]
		if got_student1 == expected_student1:
			self.log.info('OK: student1 CSV line is as expected.')
		else:
			self.fail('CSV line for student1,\nexp: {!r}\ngot: {!r}.'.format(expected_student1, got_student1))

		handler_set(['asm/attributes/student/password_policy=-'])
		update_ucr()
		or_student2 = AsmStudent.from_dn(student2_dn)
		got_student2 = or_student2.as_csv_line()
		expected_student2 = [
			s2_name, s2_name, student2.firstname, '', student2.lastname, '', email_sub, student2_name, '', school2, school1
		]
		if got_student2 == expected_student2:
			self.log.info('OK: student2 CSV line is as expected.')
		else:
			self.fail('CSV line for student2,\nexp: {!r}\ngot: {!r}.'.format(expected_student2, got_student2))

		handler_set(['asm/attributes/student/anonymize=true', 'asm/attributes/student/password_policy=6'])
		update_ucr()
		or_student1 = AsmStudent.from_dn(student1_dn)
		got_student1 = or_student1.as_csv_line()
		expected_student1 = [
			s1_name, s1_name, student1.name, '', 'No Name', '', '', student1.name, '6', school1
		]
		if got_student1 == expected_student1:
			self.log.info('OK: student1 anonymized CSV line is as expected.')
		else:
			self.fail('CSV line for student1 anonymized,\nexp: {!r}\ngot: {!r}.'.format(expected_student1, got_student1))

		last_name_anon = uts.random_name()
		handler_set(['asm/attributes/student/anonymize/last_name={}'.format(last_name_anon), 'asm/attributes/student/password_policy=8'])
		update_ucr()
		or_student1 = AsmStudent.from_dn(student1_dn)
		got_student1 = or_student1.as_csv_line()
		expected_student1 = [
			s1_name, s1_name, student1.name, '', last_name_anon, '', '', student1.name, '8', school1
		]
		if got_student1 == expected_student1:
			self.log.info('OK: student1 anonymized CSV line with static last_name is as expected.')
		else:
			self.fail('CSV line with static last_name for student1 anonymized,\nexp: {!r}\ngot: {!r}.'.format(
				expected_student1, got_student1))


if __name__ == '__main__':
	with ucr_test.UCSTestConfigRegistry():
		handler_unset(
			[
				"asm/attributes/user/email/prepend_domain",
				"asm/attributes/classes/class_number_empty",
				"asm/attributes/staff/anonymize",
				"asm/attributes/student/password_policy",
			] + [
				"asm/attributes/student/anonymize{}".format(value)
				for value in ("", "/email_address", "/first_name", "/last_name", "/middle_name", "/sis_username")
			]
		)
		Test().run()
