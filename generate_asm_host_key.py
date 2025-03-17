import contextlib

from paramiko.client import AutoAddPolicy, SSHClient
from paramiko.ssh_exception import SSHException


def main() -> None:
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())  # noqa: S507
    with contextlib.suppress(SSHException):
        client.connect("upload.appleschoolcontent.com")
    client.save_host_keys("asm_public_key")


if __name__ == "__main__":
    main()
