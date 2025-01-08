#!/usr/share/ucs-test/runner python3
## -*- coding: utf-8 -*-
## desc: test asm-upload
## tags: [apptest]
## exposure: dangerous
## packages:
##   - univention-apple-school-manager-connector
## bugs: [47623]

import os
import subprocess
import shutil
import stat
import filecmp
import json
from paramiko.client import SSHClient, AutoAddPolicy
from ucsschool.lib.models.utils import exec_cmd
from univention.admin.uldap import getMachineConnection
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils
from univention.config_registry import handler_set
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


def write_tmp_file(filename, content):
	file_path = os.path.join("/tmp", filename)
	with open(file_path, "w") as fd:
		fd.write(content)
	return file_path


class LocalHostAsASM(object):

	def __init__(self, connections):
		self.connections = connections

	def __enter__(self):
		ucr_values = [
			"asm/multiple_connections=true",
			"hosts/static/127.0.60.60=upload.appleschoolcontent.com",
			"asm/store_zip=yes",
		]
		for connection in self.connections:
			ucr_values.append(f"auth/sshd/user/{connection.get('username')}=yes")
		handler_set(ucr_values)

		os.rename("/etc/asm_public_key", "/etc/asm_public_key.backup_61test")
		client = SSHClient()
		client.set_missing_host_key_policy(AutoAddPolicy())
		for connection in self.connections:
			subprocess.check_call(["mkhomedir_helper", connection["username"]])
			self.dropbox = os.path.join(connection["home_dir"], "dropbox")
			client.connect("upload.appleschoolcontent.com", username=connection["username"], password=connection["password"])
			sftp = client.open_sftp()
			sftp.chdir(connection["home_dir"])
			sftp.mkdir("dropbox")
			client.save_host_keys("/etc/asm_public_key")
			client.close()

	def __exit__(self, *args):
		if os.path.exists("/etc/asm_public_key.backup_61test"):
			os.rename("/etc/asm_public_key.backup_61test", "/etc/asm_public_key")
		try:
			shutil.rmtree(self.dropbox)
		except OSError:
			pass


class TempUserWritableFileAnywhere(object):
	def __init__(self, path):
		self.path = path

	def __enter__(self):
		print("Creating file {!r}".format(self.path))
		with open(self.path, "w") as fp:
			os.fchmod(fp.fileno(), stat.S_IWOTH)

	def __exit__(self, *args):
		print("Deleting file {!r}...".format(self.path))
		try:
			os.unlink(self.path)
		except EnvironmentError:
			pass


class Test(ImportTestbase):
	# use_ou_cache = False  # use only uncached OUs to be certain no previous test left any object
	def create_asm_mock_user(self, OUs):
		if type(OUs) is not list:
			OUs = [OUs]
		school_class = '{}-{}'.format(OUs[0], uts.random_username())
		student_name, student_dn = self.schoolenv.create_student(
			OUs[0], classes=school_class, password="univention"
		)
		lo, po = getMachineConnection()
		user_attrs = lo.get(student_dn, attr=["homeDirectory"])
		home_dir = user_attrs["homeDirectory"][0].decode()
		return {
			"username": student_name,
			"password": "univention",
			"dn": student_dn,
			"home_dir": home_dir,
			"schools": OUs
		}

	def generate_test_data(self, users):
		config = []
		for user in users:
			password_file_path = write_tmp_file(uts.random_string(), "univention")
			config.append({
				"username": user["username"],
				"password": password_file_path,
				"school_whitelist": user["schools"],
			})
		config_file_name = f"{uts.random_string()}.json"
		config_file_path = write_tmp_file(config_file_name, json.dumps(config))
		handler_set([f"asm/config_file={config_file_path}"])
		return config

	def test(self):
		connection_1 = self.create_asm_mock_user(self.ou_A.name)
		connection_2 = self.create_asm_mock_user([self.ou_B.name, self.ou_C.name])
		testuser_c = self.create_asm_mock_user(self.ou_C.name)
		self.generate_test_data([connection_1, connection_2])
		self.test_upload(connection_1, connection_2)

	def test_upload(self, connection_1, connection_2):
		remote_path = "/archive.zip"
		with ucr_test.UCSTestConfigRegistry(), LocalHostAsASM(
			(connection_1, connection_2)), TempUserWritableFileAnywhere(remote_path):
			cmd = ["/usr/sbin/asm-upload"]
			print("Executing {!r}...".format(cmd))
			returncode, stdout, stderr = exec_cmd(cmd)
			print("-> returncode={}".format(returncode))
			print("-> stdout={}".format(stdout))
			print("-> stderr={}".format(stderr))
			if returncode:
				utils.fail("{!r} returned {}.)".format(cmd, returncode))
			return


if __name__ == "__main__":
	test = Test()
	test.run()
