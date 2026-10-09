#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: set up Keycloak as the identity provider of Apple School Manager with asm-setup-keycloak
## tags: [apptest]  # noqa: ERA001
## exposure: dangerous  # noqa: ERA001
## packages:
##   - univention-apple-school-manager-connector

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import subprocess
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest
import univention.testing.strings as uts
from keycloak import KeycloakAdmin
from univention.asm import keycloak
from univention.config_registry import ConfigRegistry

REALM = "ucs"


@pytest.fixture
def base_url() -> str:
    ucr = ConfigRegistry()
    ucr.load()
    return str(ucr.get("ucs/server/sso/uri", f"https://ucs-sso-ng.{ucr['domainname']}/".lower())).rstrip(
        "/"
    )


@pytest.fixture
def admin(base_url: str) -> KeycloakAdmin:
    return KeycloakAdmin(
        server_url=f"{base_url}/",
        username="admin",
        password=Path("/etc/keycloak.secret").read_text().strip(),
        realm_name=REALM,
        user_realm_name="master",
        verify=True,
    )


@pytest.fixture
def names(admin: KeycloakAdmin) -> Iterator[tuple[str, str]]:
    client_id = f"asm-test-{uts.random_name()}"
    username = uts.random_username()
    yield client_id, username
    if (user_id := admin.get_user_id(username)) is not None:
        admin.delete_user(user_id)
    if (client_uuid := admin.get_client_id(client_id)) is not None:
        admin.delete_client(client_uuid)


def run_setup(client_id: str, username: str, password_file: Path) -> dict[str, str]:
    cmd = [
        "/usr/sbin/asm-setup-keycloak",
        "--client-id",
        client_id,
        "--user",
        username,
        "--password-file",
        str(password_file),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print(result.stdout, result.stderr)
    assert result.returncode == 0, result.stderr
    values = {}
    for line in result.stdout.splitlines():
        key, sep, value = line.partition(":")
        if sep and key in {"Client ID", "Client Secret", "SSF URL", "OIDC URL"}:
            values[key] = value.strip()
    return values


def test_asm_setup_keycloak(
    admin: KeycloakAdmin, base_url: str, names: tuple[str, str], tmp_path: Path
) -> None:
    client_id, username = names
    password_file = tmp_path / "password"
    password_file.write_text(uts.random_string(20))

    values = run_setup(client_id, username, password_file)

    assert values["Client ID"] == client_id
    assert values["SSF URL"] == f"{base_url}/realms/{REALM}/.well-known/ssf-configuration"
    assert values["OIDC URL"] == f"{base_url}/realms/{REALM}/.well-known/openid-configuration"
    with urllib.request.urlopen(values["SSF URL"], timeout=30) as response:  # noqa: S310
        assert response.status == 200
    assert admin.get_realm(REALM)["attributes"]["ssf.transmitterEnabled"] == "true"
    client_uuid = admin.get_client_id(client_id)
    assert values["Client Secret"] == admin.get_client_secrets(client_uuid)["value"]
    client = admin.get_client(client_uuid)
    assert client["attributes"]["ssf.enabled"] == "true"
    assert client["attributes"]["ssf.requiredRole"] == f"{client_id}.{keycloak.SSF_ADMIN_ROLE}"
    assert {scope["name"] for scope in admin.get_client_default_client_scopes(client_uuid)} >= set(
        keycloak.DEFAULT_CLIENT_SCOPES
    )
    user_id = admin.get_user_id(username)
    assert keycloak.SSF_ADMIN_ROLE in {
        role["name"] for role in admin.get_client_roles_of_user(user_id, client_uuid)
    }

    assert run_setup(client_id, username, password_file) == values
