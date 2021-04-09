#!/usr/share/ucs-test/runner python
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
import filecmp
from paramiko.client import SSHClient, AutoAddPolicy
from ucsschool.lib.models.utils import exec_cmd
from univention.admin.uldap import getMachineConnection
import univention.testing.strings as uts
import univention.testing.ucr as ucr_test
import univention.testing.utils as utils
from univention.config_registry import handler_set
from univention.testing.ucsschool.importusers_cli_v2 import ImportTestbase


class LocalHostAsASM(object):

	def __init__(self, username, password, home_dir, school_name):
		self.username = username
		self.password = password
		self.school_name = school_name
		subprocess.check_call(["mkhomedir_helper", self.username])
		self.home_dir = home_dir
		self.dropbox = os.path.join(home_dir, "dropbox")

	def __enter__(self):
		handler_set([
			"hosts/static/127.0.60.60=upload.appleschoolcontent.com",
			"asm/username={}".format(self.username),
			"asm/store_zip=yes",
			"asm/school_whitelist={}".format(self.school_name),
			"auth/sshd/user/{}=yes".format(self.username),
		])
		os.rename("/etc/asm_public_key", "/etc/asm_public_key.backup_60test")
		if os.path.exists("/etc/asm.secret"):
			os.rename("/etc/asm.secret", "/etc/asm.secret.backup_60test")
		with open("/etc/asm.secret", "w") as asm_secret_file:
			asm_secret_file.write(self.password)
		client = SSHClient()
		client.set_missing_host_key_policy(AutoAddPolicy())
		client.connect("upload.appleschoolcontent.com", username=self.username, password=self.password)
		sftp = client.open_sftp()
		sftp.chdir(self.home_dir)
		sftp.mkdir("dropbox")
		client.save_host_keys("/etc/asm_public_key")
		client.close()

	def __exit__(self, *args):
		os.rename("/etc/asm_public_key.backup_60test", "/etc/asm_public_key")
		if os.path.exists("/etc/asm.secret.backup_60test"):
			os.rename("/etc/asm.secret.backup_60test", "/etc/asm.secret")
		try:
			shutil.rmtree(self.dropbox)
		except OSError:
				pass


class TempUserWritableFileAnywhere(object):
	def __init__(self, path, uid, gid):
		self.path = path
		self.uid = uid
		self.gid = gid

	def __enter__(self):
		print("Creating file {!r} with uid={!r} and gid={!r}...".format(self.path, self.uid, self.gid))
		with open(self.path, "w") as fp:
			os.fchown(fp.fileno(), self.uid, self.gid)

	def __exit__(self, *args):
		print("Deleting file {!r}...".format(self.path))
		try:
			os.unlink(self.path)
		except EnvironmentError:
			pass


class Test(ImportTestbase):
	# use_ou_cache = False  # use only uncached OUs to be certain no previous test left any object
	ou_B = None
	ou_C = None

	def test(self):
		school_class = '{}-{}'.format(self.ou_A.name, uts.random_username())
		student1_name, student1_dn = self.schoolenv.create_student(
			self.ou_A.name, classes=school_class, password="univention"
		)
		lo, po = getMachineConnection()
		user_attrs = lo.get(student1_dn, attr=["homeDirectory", "uidNumber", "gidNumber"])
		home_dir = user_attrs["homeDirectory"][0]
		uid = int(user_attrs["uidNumber"][0])
		gid = int(user_attrs["gidNumber"][0])
		remote_path = "/archive.zip"
		with ucr_test.UCSTestConfigRegistry(), LocalHostAsASM(
				student1_name, "univention", home_dir, self.ou_A.name
		), TempUserWritableFileAnywhere(remote_path, uid, gid):
			cmd = ["/usr/sbin/asm-upload"]
			print("Executing {!r}...".format(cmd))
			returncode, stdout, stderr = exec_cmd(cmd)
			print("-> returncode={}".format(returncode))
			print("-> stdout={}".format(stdout))
			print("-> stderr={}".format(stderr))
			if returncode:
				utils.fail("{!r} returned {}.)".format(cmd, returncode))
			for line in stderr.split("\n"):
				if line.startswith("The uploaded zip is stored in: "):
					zip_path = line.split()[-1]
					print("Comparing zip_path={!r} and remote_path={!r}...".format(
						zip_path, remote_path)
					)
					if not filecmp.cmp(zip_path, remote_path, shallow=False):
						utils.fail("ZIP file was not correctly uploaded")
					return
			else:
				utils.fail("Something with the upload seems to be broken.")


if __name__ == "__main__":
	test = Test()
	test.run()
