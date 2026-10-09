#!/usr/share/ucs-test/runner pytest-3 -s -l -v
## desc: test the Keycloak setup for Apple School Manager against an in-memory Keycloak
## tags: [apptest]  # noqa: ERA001
## exposure: safe  # noqa: ERA001
## packages:
##   - python3-univention-apple-school-manager-connector

# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

import copy
import re
import uuid
from typing import Any

import pytest
from univention.asm import keycloak

REALM = "ucs"
BASE_URL = "https://ucs-sso-ng.example.com/"
USER = keycloak.AdminUser(username="asm", first_name="A", last_name="B", email="asm@example.com")


class FakeKeycloakAdmin:
    """Keeps a realm in memory and counts the calls that change it."""

    def __init__(self) -> None:
        self.realm: dict[str, Any] = {"attributes": {"keep": "me"}}
        self.scopes: dict[str, dict[str, Any]] = {}
        self.clients: dict[str, dict[str, Any]] = {}
        self.default_scopes: dict[str, list[str]] = {}
        self.optional_scopes: dict[str, list[str]] = {}
        self.roles: dict[str, dict[str, dict[str, Any]]] = {}
        self.users: dict[str, dict[str, Any]] = {}
        self.user_roles: dict[tuple[str, str], list[dict[str, Any]]] = {}
        self.passwords: dict[str, str] = {}
        self.writes = 0
        self.add_scope("offline_access", {})

    def add_scope(self, name: str, attributes: dict[str, str]) -> str:
        scope_id = str(uuid.uuid4())
        self.scopes[scope_id] = {"id": scope_id, "name": name, "attributes": dict(attributes)}
        return scope_id

    def get_realm(self, realm_name: str) -> dict[str, Any]:
        assert realm_name == REALM
        return copy.deepcopy(self.realm)

    def update_realm(self, realm_name: str, payload: dict[str, Any]) -> None:
        assert realm_name == REALM
        self.writes += 1
        self.realm.update(copy.deepcopy(payload))

    def get_client_scope_by_name(self, client_scope_name: str) -> dict[str, Any] | None:
        for scope in self.scopes.values():
            if scope["name"] == client_scope_name:
                return copy.deepcopy(scope)
        return None

    def create_client_scope(self, payload: dict[str, Any], skip_exists: bool = False) -> str:  # noqa: ARG002, FBT001
        self.writes += 1
        return self.add_scope(payload["name"], payload.get("attributes", {}))

    def update_client_scope(self, client_scope_id: str, payload: dict[str, Any]) -> None:
        self.writes += 1
        self.scopes[client_scope_id] = copy.deepcopy(payload)

    def get_client_id(self, client_id: str) -> str | None:
        return next(
            (uid for uid, client in self.clients.items() if client["clientId"] == client_id), None
        )

    def get_client(self, client_id: str) -> dict[str, Any]:
        return copy.deepcopy(self.clients[client_id])

    def create_client(self, payload: dict[str, Any], skip_exists: bool = False) -> str:  # noqa: ARG002, FBT001
        self.writes += 1
        client_uuid = str(uuid.uuid4())
        self.clients[client_uuid] = {**copy.deepcopy(payload), "id": client_uuid, "secret": "s3cr3t"}
        self.default_scopes[client_uuid] = []
        offline_access = self.get_client_scope_by_name("offline_access")
        assert offline_access is not None
        self.optional_scopes[client_uuid] = [offline_access["id"]]
        self.roles[client_uuid] = {}
        return client_uuid

    def update_client(self, client_id: str, payload: dict[str, Any]) -> None:
        self.writes += 1
        self.clients[client_id] = copy.deepcopy(payload)

    def get_client_default_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        return [
            {"id": scope_id, "name": self.scopes[scope_id]["name"]}
            for scope_id in self.default_scopes[client_id]
        ]

    def add_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: dict[str, Any],  # noqa: ARG002
    ) -> None:
        """Like Keycloak, ignore a scope that is already attached as optional."""
        if client_scope_id in self.optional_scopes[client_id]:
            return
        self.writes += 1
        self.default_scopes[client_id].append(client_scope_id)

    def get_client_optional_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        return [
            {"id": scope_id, "name": self.scopes[scope_id]["name"]}
            for scope_id in self.optional_scopes[client_id]
        ]

    def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> None:
        self.writes += 1
        self.optional_scopes[client_id].remove(client_scope_id)

    def create_client_role(
        self,
        client_role_id: str,
        payload: dict[str, Any],
        skip_exists: bool = False,  # noqa: FBT001
    ) -> str:
        if payload["name"] in self.roles[client_role_id]:
            assert skip_exists
            return str(payload["name"])
        self.writes += 1
        self.roles[client_role_id][payload["name"]] = {"id": str(uuid.uuid4()), "name": payload["name"]}
        return str(payload["name"])

    def get_client_role(self, client_id: str, role_name: str) -> dict[str, Any]:
        return copy.deepcopy(self.roles[client_id][role_name])

    def get_user_id(self, username: str) -> str | None:
        return next(
            (uid for uid, user in self.users.items() if user["username"] == username.lower()), None
        )

    def get_user(self, user_id: str) -> dict[str, Any]:
        return copy.deepcopy(self.users[user_id])

    def create_user(self, payload: dict[str, Any], exist_ok: bool = False) -> str:  # noqa: ARG002, FBT001
        self.writes += 1
        user_id = str(uuid.uuid4())
        self.users[user_id] = {**copy.deepcopy(payload), "id": user_id}
        return user_id

    def set_user_password(self, user_id: str, password: str, temporary: bool = True) -> None:  # noqa: FBT001
        assert not temporary
        self.writes += 1
        self.passwords[user_id] = password

    def get_client_roles_of_user(self, user_id: str, client_id: str) -> list[dict[str, Any]]:
        return copy.deepcopy(self.user_roles.get((user_id, client_id), []))

    def assign_client_role(self, user_id: str, client_id: str, roles: list[dict[str, Any]]) -> None:
        self.writes += 1
        self.user_roles.setdefault((user_id, client_id), []).extend(copy.deepcopy(roles))

    def get_client_secrets(self, client_id: str) -> dict[str, Any]:
        return {"type": "secret", "value": self.clients[client_id]["secret"]}


@pytest.fixture
def admin() -> FakeKeycloakAdmin:
    return FakeKeycloakAdmin()


def run_setup(admin: FakeKeycloakAdmin, client_id: str = "apple-asm") -> keycloak.SetupResult:
    return keycloak.KeycloakSetup(admin, BASE_URL, REALM, report=lambda _message: None).run(
        client_id, USER, lambda: "password"
    )


def test_setup_creates_everything(admin: FakeKeycloakAdmin) -> None:
    result = run_setup(admin)
    assert result == keycloak.SetupResult(
        client_id="apple-asm",
        client_secret="s3cr3t",
        ssf_url="https://ucs-sso-ng.example.com/realms/ucs/.well-known/ssf-configuration",
        oidc_url="https://ucs-sso-ng.example.com/realms/ucs/.well-known/openid-configuration",
    )
    assert admin.realm["attributes"] == {"keep": "me", "ssf.transmitterEnabled": "true"}
    for name in keycloak.SSF_SCOPES:
        scope = admin.get_client_scope_by_name(name)
        assert scope is not None
        assert scope["attributes"]["include.in.token.scope"] == "true"
    client_uuid = admin.get_client_id("apple-asm")
    assert client_uuid is not None
    client = admin.get_client(client_uuid)
    assert client["publicClient"] is False
    assert client["redirectUris"] == [keycloak.APPLE_REDIRECT_URI]
    assert client["attributes"]["ssf.enabled"] == "true"
    assert client["attributes"]["ssf.requiredRole"] == "apple-asm.ssf-admin"
    assert {scope["name"] for scope in admin.get_client_default_client_scopes(client_uuid)} == set(
        keycloak.DEFAULT_CLIENT_SCOPES
    )
    user_id = admin.get_user_id("asm")
    assert user_id is not None
    assert admin.passwords[user_id] == "password"
    assert [role["name"] for role in admin.get_client_roles_of_user(user_id, client_uuid)] == [
        "ssf-admin"
    ]


def test_second_run_changes_nothing(admin: FakeKeycloakAdmin) -> None:
    first = run_setup(admin)
    writes = admin.writes
    assert run_setup(admin) == first
    assert admin.writes == writes


def test_setup_repairs_a_changed_client(admin: FakeKeycloakAdmin) -> None:
    run_setup(admin)
    client_uuid = admin.get_client_id("apple-asm")
    assert client_uuid is not None
    admin.clients[client_uuid]["attributes"]["ssf.validPushUrls"] = "https://example.com/*"
    admin.clients[client_uuid]["attributes"]["custom"] = "kept"
    run_setup(admin)
    attributes = admin.get_client(client_uuid)["attributes"]
    assert attributes["ssf.validPushUrls"] == keycloak.APPLE_PUSH_URL
    assert attributes["custom"] == "kept"


def test_existing_scope_gets_included_in_token_scope(admin: FakeKeycloakAdmin) -> None:
    admin.add_scope("ssf.read", {"include.in.token.scope": "false"})
    run_setup(admin)
    scope = admin.get_client_scope_by_name("ssf.read")
    assert scope is not None
    assert scope["attributes"]["include.in.token.scope"] == "true"


def test_user_from_ucs_is_refused(admin: FakeKeycloakAdmin) -> None:
    admin.users["ldap-user"] = {"id": "ldap-user", "username": "asm", "federationLink": "ldap-provider"}
    with pytest.raises(keycloak.KeycloakSetupError, match="comes from UCS"):
        run_setup(admin)


def test_client_id_with_a_dot_is_refused(admin: FakeKeycloakAdmin) -> None:
    with pytest.raises(keycloak.KeycloakSetupError, match="client ID"):
        run_setup(admin, client_id="apple.asm")


@pytest.mark.parametrize("version", ["26.7.2-nubus1", "26.7.2-nubus2", "26.7.4-nubus1", "27.0.0-nubus1"])
def test_supported_keycloak_app_version(version: str) -> None:
    keycloak.check_keycloak_app_version(version)


@pytest.mark.parametrize("version", ["26.6.1-nubus3", "26.7.1-nubus1", "26.7.2", "25.0.6-ucs2"])
def test_unsupported_keycloak_app_version(version: str) -> None:
    with pytest.raises(keycloak.KeycloakSetupError, match=re.escape(keycloak.MIN_KEYCLOAK_APP_VERSION)):
        keycloak.check_keycloak_app_version(version)


def test_missing_keycloak_app() -> None:
    with pytest.raises(keycloak.KeycloakSetupError, match="isn't installed"):
        keycloak.check_keycloak_app_version(None)
