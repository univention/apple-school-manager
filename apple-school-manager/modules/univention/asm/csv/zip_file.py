# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Classes the produce ASM ZIP files containing CSV files.

See https://support.apple.com/en-us/HT207029
"""

import logging
import os
import shutil
import sys
import tempfile
import zipfile
from collections.abc import Iterable

from univention.admin import uexceptions

from .csv_file import create_csv_files


class AsmZipFile:
    """Class to create a ZIP file with ASM CSV files."""

    def __init__(self, file_path: str, ou_whitelist: Iterable[str] | None = None) -> None:
        """
        :param str file_path: file path to write ZIP to
        :param ou_whitelist: list of schools/OUs that should be considered when looking for LDAP objects. No limit if empty or None.
        :type ou_whitelist: list(str) or None
        """
        self.file_path: str = file_path
        self.ou_whitelist = ou_whitelist
        self.csv_files: Iterable[str] = []
        self.logger = logging.getLogger(__name__)

    def create_csv_files(self, tmp_dir: str) -> Iterable[str]:
        """
        Create ASM CSV files.

        File names will be saved to :py:attr:`self.file_path`.

        :return: list of files created
        :rtype: list(str)
        """
        self.logger.debug("Creating CSV files in %s...", tmp_dir)
        self.csv_files = create_csv_files(tmp_dir, self.ou_whitelist)
        if not self.csv_files:
            msg = "No CSV files were created."
            raise FileNotFoundError(msg)
        self.logger.debug("Created CSV files: %s.", ", ".join(sorted(self.csv_files)))
        return self.csv_files

    def write_zip(self, file_path: str | None = None, delete_csv_files: bool | None = True) -> str:  # noqa: FBT001
        """
        Compress CSV files into a ZIP file. An existing file will be overwritten.

        If :py:attr:`self.csv_files` is non-empty, those files will be used,
        else they will be created.

        :param str file_path: path to write ZIP to, if unset will be written to :py:attr:`self.file_path`
        :param bool delete_csv_files: whether the CSV files should be removed afterwards
        :return: path to the created ZIP file
        :rtype: str
        """
        file_path = file_path or self.file_path
        tmp_dir = tempfile.mkdtemp()
        if not file_path:
            msg = "ZIP file path is empty."
            raise ValueError(msg)
        self.logger.info("Creating ZIP file in %s...", file_path)
        if self.csv_files:
            self.logger.debug("Using existing CSV files: %s.", ", ".join(sorted(self.csv_files)))
        else:
            try:
                self.csv_files = self.create_csv_files(tmp_dir)
            except uexceptions.valueInvalidSyntax:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                self.logger.exception("Error during creation of csv files. Abort asm-upload.")
                sys.exit(1)
        self.logger.debug("Writing ZIP file to %s...", file_path)
        with open(file_path, "wb") as fp, zipfile.ZipFile(fp, "w", zipfile.ZIP_DEFLATED) as zf:
            os.fchmod(fp.fileno(), 0o600)
            for path in sorted(self.csv_files):
                zf.write(path, os.path.basename(path))
        self.logger.debug("Done writing ZIP file.")
        if delete_csv_files:
            self.logger.debug("Deleting temporary CSV files and directory...")
            shutil.rmtree(tmp_dir, ignore_errors=True)
        self.logger.info("Finished creating ZIP file.")
        return file_path
