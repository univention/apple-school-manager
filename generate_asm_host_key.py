from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import SSHException


def main():
	client = SSHClient()
	client.set_missing_host_key_policy(AutoAddPolicy())
	try:
		client.connect("upload.appleschoolcontent.com")
	except SSHException:
		pass
	client.save_host_keys("asm_public_key")


if __name__ == "__main__":
	main()
