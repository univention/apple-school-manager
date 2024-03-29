#!/usr/share/ucs-test/runner python
## -*- coding: utf-8 -*-
## desc: test staff model/CSV generation
## tags: [apptest]
## exposure: dangerous
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622]

from univention.config_registry import handler_unset
import univention.testing.ucr as ucr_test
from ucsschool.lib.models.user import Teacher, TeachersAndStaff
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.config_registry import handler_set
from univention.asm.models.staff import AsmStaff
from univention.asm.utils import get_person_id, update_ucr
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


class Test(ImportTestbase):
	ou_C = None

	def test(self):
		subdomain = uts.random_name()
		handler_set(['asm/attributes/user/email/prepend_domain={}'.format(subdomain)])

		school1 = self.ou_A.name
		school2 = self.ou_B.name

		teacher1_name, teacher1_dn = self.schoolenv.create_teacher(school1)
		email_local = uts.random_name()
		email = '{}@{}'.format(email_local, self.maildomain)
		email_sub = '{}@{}.{}'.format(email_local, subdomain, self.maildomain)
		teacher2_name, teacher2_dn = self.schoolenv.create_teacher_and_staff(
			school2, schools=[school1, school2], mailaddress=email)
		t1_id_attr, t1_lo = get_person_id(teacher1_dn, 'staff', [])
		t1_name = t1_lo[t1_id_attr][0]
		t2_id_attr, t2_lo = get_person_id(teacher2_dn, 'staff', [])
		t2_name = t2_lo[t2_id_attr][0]
		self.log.info('Created teacher1: %r (%s, %s)', teacher1_name, teacher1_dn, t1_name)
		self.log.info('Created teacher2: %r (%s, %s)', teacher2_name, teacher2_dn, t2_name)

		# check if this system has a schema that supports a middle name
		teacher1 = Teacher.from_dn(teacher1_dn, None, self.lo)
		teacher_udm_obj = teacher1.get_udm_object(self.lo)
		for attr in ('middleName', 'initials', 'oxMiddleName'):
			if attr in teacher_udm_obj:
				middle_name = uts.random_name(length=5)
				self.log.info('*** Adding middle name to teacher1: %r...', middle_name)
				teacher_udm_obj[attr] = middle_name
				teacher_udm_obj.modify()
				utils.verify_ldap_object(teacher1_dn, {attr: [middle_name]})
				# reload object just to be safe
				teacher1 = Teacher.from_dn(teacher1_dn, None, self.lo)
				break
		else:
			self.log.info('*** No LDAP schema for middle name attribute found.')
			middle_name = ''

		teacher2 = TeachersAndStaff.from_dn(teacher2_dn, None, self.lo)

		or_teacher1 = AsmStaff.from_dn(teacher1_dn)
		got_teacher1 = or_teacher1.as_csv_line()
		expected_teacher1 = [
			t1_name, t1_name, teacher1.firstname, middle_name, teacher1.lastname, '', teacher1_name, school1
		]
		if got_teacher1 == expected_teacher1:
			self.log.info('OK: teacher1 CSV line is as expected.')
		else:
			self.fail('CSV line for teacher1,\nexp: {!r}\ngot: {!r}.'.format(expected_teacher1, got_teacher1))

		or_teacher2 = AsmStaff.from_dn(teacher2_dn)
		got_teacher2 = or_teacher2.as_csv_line()
		expected_teacher2 = [
			t2_name, t2_name, teacher2.firstname, '', teacher2.lastname, email_sub, teacher2_name, school2, school1
		]
		if got_teacher2 == expected_teacher2:
			self.log.info('OK: teacher2 CSV line is as expected.')
		else:
			self.fail('CSV line for teacher2,\nexp: {!r}\ngot: {!r}.'.format(expected_teacher2, got_teacher2))

		handler_set(['asm/attributes/staff/anonymize=true'])
		update_ucr()
		or_teacher1 = AsmStaff.from_dn(teacher1_dn)
		got_teacher1 = or_teacher1.as_csv_line()
		expected_teacher1 = [t1_name, t1_name, teacher1.name, '', 'No Name', '', teacher1.name, school1]
		if got_teacher1 == expected_teacher1:
			self.log.info('OK: teacher1 anonymized CSV line is as expected.')
		else:
			self.fail('CSV line for teacher1 anonymized,\nexp: {!r}\ngot: {!r}'.format(expected_teacher1, got_teacher1))

		first_name_anon = uts.random_name()
		handler_set(['asm/attributes/staff/anonymize/first_name={}'.format(first_name_anon)])
		update_ucr()
		or_teacher1 = AsmStaff.from_dn(teacher1_dn)
		got_teacher1 = or_teacher1.as_csv_line()
		expected_teacher1 = [t1_name, t1_name, first_name_anon, '', 'No Name', '', teacher1.name, school1]
		if got_teacher1 == expected_teacher1:
			self.log.info('OK: teacher1 anonymized CSV line with static first_name is as expected.')
		else:
			self.fail('CSV line with static first_name for teacher1 anonymized,\nexp: {!r}\ngot: {!r}.'.format(
					expected_teacher1, got_teacher1))


if __name__ == '__main__':
	with ucr_test.UCSTestConfigRegistry():
		handler_unset([
			"asm/attributes/user/email/prepend_domain",
			"asm/attributes/classes/class_number_empty",
			"asm/attributes/student/anonymize",
		])
		handler_unset(["asm/attributes/staff/anonymize{}".format(value) for value in ("", "/email_address", "/first_name", "/last_name", "/middle_name", "/sis_username")])
		Test().run()
