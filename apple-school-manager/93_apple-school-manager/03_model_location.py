#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test location model/CSV generation
## tags: [apptest]
## exposure: dangerous
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47622]

from ldap.filter import filter_format
from ucsschool.lib.models.school import School
from univention.config_registry import handler_unset
import univention.testing.ucr as ucr_test
import univention.testing.strings as uts
import univention.testing.utils as utils
from univention.asm.models.location import AsmLocation
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


class Test(ImportTestbase):
	ou_C = None

	def test(self):
		school1 = self.ou_A.name
		school2 = self.ou_B.name

		filter_s = filter_format('(&(objectClass=ucsschoolOrganizationalUnit)(ou=%s))', (school1,))
		res = self.lo.search(filter=filter_s)
		if len(res) != 1:
			self.fail('School 1 not found: search with filter={!r} did not return 1 result:\n{}'.format(
				filter_s, res))
		school1_dn = res[0][0]
		school1_attrs = res[0][1]

		filter_s = filter_format('(&(objectClass=ucsschoolOrganizationalUnit)(ou=%s))', (school2,))
		res = self.lo.searchDn(filter=filter_s)
		if len(res) != 1:
			self.fail('School 2 not found: search with filter={!r} did not return 1 result:\n{}'.format(
				filter_s, res))
		school2_dn = res[0]

		display_name = uts.random_string()
		self.log.info('Setting display_name of school2 (%s) to %r.', school2, display_name)
		sc2 = School.from_dn(school2_dn, self.ou_B.name, self.lo)
		sc2.display_name = display_name
		sc2.modify(self.lo)
		utils.verify_ldap_object(school2_dn, {'displayName': [display_name]})

		loc1 = AsmLocation.from_dn(school1_dn)
		got_loc1 = loc1.as_csv_line()
		expected_loc1 = [school1, school1_attrs.get('displayName', [None])[0].decode('utf-8') or school1]
		if got_loc1 == expected_loc1:
			self.log.info('OK: location1 CSV line is as expected.')
		else:
			self.fail('Expected CSV line for location1: {!r}, got: {!r}.'.format(expected_loc1, got_loc1))

		loc2 = AsmLocation.from_dn(school2_dn)
		got_loc2 = loc2.as_csv_line()
		expected_loc2 = [school2, display_name]
		if got_loc2 == expected_loc2:
			self.log.info('OK: location2 CSV line is as expected.')
		else:
			self.fail('Expected CSV line for location2: {!r}, got: {!r}.'.format(expected_loc2, got_loc2))


if __name__ == '__main__':
	with ucr_test.UCSTestConfigRegistry():
		handler_unset([
			"asm/attributes/user/email/prepend_domain",
			"asm/attributes/classes/class_number_empty",
			"asm/attributes/staff/anonymize",
			"asm/attributes/student/anonymize",
		])
		Test().run()
