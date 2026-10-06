# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

from collections.abc import Callable

import pytest
from univention.admin.uldap import access
from univention.testing.ucr import UCSTestConfigRegistry
from univention.testing.ucsschool.ucs_test_school import UCSTestSchool

pytest_plugins = ["univention.testing.conftest", "univention.testing.ucsschool.conftest"]


@pytest.fixture
def lo(schoolenv: UCSTestSchool, ucr: UCSTestConfigRegistry) -> access:
    has_admin_credentials = ucr["server/role"] in ("domaincontroller_master", "domaincontroller_backup")
    return schoolenv.open_ldap_connection(admin=has_admin_credentials)


@pytest.fixture
def maildomain(schoolenv: UCSTestSchool, ucr: UCSTestConfigRegistry, mail_domain: str) -> str:
    if mail_domain not in ucr.get("mail/hosteddomains", ""):
        schoolenv.udm.create_object(
            "mail/domain",
            position=f"cn=domain,cn=mail,{ucr['ldap/base']}",
            name=mail_domain,
            ignore_exists=True,
        )
    return mail_domain


@pytest.fixture
def create_ous(
    schoolenv: UCSTestSchool,
    ucr: UCSTestConfigRegistry,
    maildomain: str,  # noqa: ARG001
) -> Callable[..., list[tuple[str, str]]]:
    def _create_ous(count: int, *, use_cache: bool = True) -> list[tuple[str, str]]:
        ous: list[tuple[str, str]] = schoolenv.create_multiple_ous(
            count, name_edudc=ucr.get("hostname"), use_cache=use_cache
        )
        return ous

    return _create_ous
