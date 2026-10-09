# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Set up Keycloak as the identity provider of Apple School Manager.

Apple School Manager federates the sign-in of its Managed Apple Accounts to an
OIDC identity provider that also acts as an SSF transmitter. This module
creates on the Keycloak side what the manual chapter "Keycloak as identity
provider for ASM" describes, and leaves anything that already matches alone.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

APPLE_REDIRECT_URI = "https://gsa-ws.apple.com/grandslam/GsService2/acs"
APPLE_PUSH_URL = "https://federation.apple.com/feeds/school/caep/*"
SSF_SCOPES = ("ssf.manage", "ssf.read")
DEFAULT_CLIENT_SCOPES = (*SSF_SCOPES, "offline_access")
SSF_ADMIN_ROLE = "ssf-admin"
TRANSMITTER_ATTRIBUTE = "ssf.transmitterEnabled"
MIN_KEYCLOAK_APP_VERSION = "26.7.2-nubus1"
CLIENT_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]+")


class KeycloakSetupError(Exception):
    """The setup can't continue, the message tells the administrator why."""


@dataclass(frozen=True)
class AdminUser:
    username: str
    first_name: str
    last_name: str
    email: str


@dataclass(frozen=True)
class SetupResult:
    """The values that Apple School Manager asks for."""

    client_id: str
    client_secret: str
    ssf_url: str
    oidc_url: str


def check_keycloak_app_version(version: str | None) -> None:
    """
    Make sure that the Keycloak app supports SSF.

    :param version: the installed version, such as ``26.7.2-nubus1``, None if not installed
    :raises KeycloakSetupError: if the app is missing or too old
    """
    if not version:
        msg = "The Keycloak app isn't installed on this system."
        raise KeycloakSetupError(msg)
    if _version_key(version) < _version_key(MIN_KEYCLOAK_APP_VERSION):
        msg = (
            f"The Keycloak app is version {version}, "
            f"but the SSF support needs version {MIN_KEYCLOAK_APP_VERSION} or later."
        )
        raise KeycloakSetupError(msg)


def _version_key(version: str) -> tuple[tuple[int, ...], int]:
    upstream, _, suffix = version.partition("-")
    numbers = tuple(int(part) for part in re.findall(r"\d+", upstream))
    build = re.search(r"\d+", suffix)
    return numbers, int(build.group()) if build else 0


def check_client_id(client_id: str) -> None:
    """
    Make sure that `client_id` works as the prefix of the required SSF role.

    Keycloak reads ``ssf.requiredRole`` as ``CLIENT.ROLE`` and splits it at the
    first dot, so a client ID with a dot never matches its own role.

    :raises KeycloakSetupError: if the client ID contains other characters
    """
    if not CLIENT_ID_PATTERN.fullmatch(client_id):
        msg = f"The client ID {client_id!r} may only contain letters, digits, '_', and '-'."
        raise KeycloakSetupError(msg)


def client_attributes(client_id: str) -> dict[str, str]:
    """Return the client attributes for login and the SSF receiver."""
    return {
        "post.logout.redirect.uris": "+",
        "pkce.code.challenge.method": "",
        "ssf.enabled": "true",
        "ssf.profile": "SSE_CAEP",
        "ssf.defaultSubjects": "NONE",
        "ssf.userSubjectFormat": "iss_sub",
        "ssf.autoNotifyOnLogin": "true",
        "ssf.autoVerifyStream": "true",
        "ssf.verificationDelayMillis": "1500",
        "ssf.requiredRole": f"{client_id}.{SSF_ADMIN_ROLE}",
        "ssf.allowedDeliveryMethods": "push",
        "ssf.validPushUrls": APPLE_PUSH_URL,
        "ssf.supportedEvents": "CaepCredentialChange,CaepSessionRevoked",
        "ssf.allowEmitEvents": "true",
        "ssf.emitOnlyEvents": "CaepSessionRevoked",
    }


def client_representation(client_id: str, current: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Return the client as Apple School Manager needs it.

    Settings of `current` that the setup doesn't manage stay as they are.
    """
    representation = dict(current or {})
    representation.update(
        clientId=client_id,
        protocol="openid-connect",
        publicClient=False,
        standardFlowEnabled=True,
        implicitFlowEnabled=False,
        directAccessGrantsEnabled=False,
        serviceAccountsEnabled=False,
        redirectUris=[APPLE_REDIRECT_URI],
    )
    representation["attributes"] = {
        **(representation.get("attributes") or {}),
        **client_attributes(client_id),
    }
    return representation


class KeycloakSetup:
    """
    Apply the setup to one realm.

    :param admin: a :py:class:`keycloak.KeycloakAdmin` session for `realm`
    """

    def __init__(
        self,
        admin: Any,  # noqa: ANN401
        base_url: str,
        realm: str,
        report: Callable[[str], None] = print,
    ) -> None:
        self.admin = admin
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.report = report

    def run(self, client_id: str, user: AdminUser, ask_password: Callable[[], str]) -> SetupResult:
        """
        Create or update everything and return the values for Apple School Manager.

        :param ask_password: returns the password for `user`, only called if the user is new
        """
        check_client_id(client_id)
        self.enable_transmitter()
        self.ensure_ssf_scopes()
        client_uuid = self.ensure_client(client_id)
        self.ensure_default_scopes(client_uuid)
        role = self.ensure_role(client_uuid)
        self.ensure_user(user, client_uuid, role, ask_password)
        return SetupResult(
            client_id=client_id,
            client_secret=self.admin.get_client_secrets(client_uuid)["value"],
            ssf_url=f"{self.base_url}/realms/{self.realm}/.well-known/ssf-configuration",
            oidc_url=f"{self.base_url}/realms/{self.realm}/.well-known/openid-configuration",
        )

    def enable_transmitter(self) -> None:
        attributes = dict(self.admin.get_realm(self.realm).get("attributes") or {})
        if attributes.get(TRANSMITTER_ATTRIBUTE) == "true":
            return
        attributes[TRANSMITTER_ATTRIBUTE] = "true"
        self.admin.update_realm(self.realm, {"attributes": attributes})
        self.report(f"Turned the realm {self.realm!r} into an SSF transmitter.")

    def ensure_ssf_scopes(self) -> None:
        wanted = {"include.in.token.scope": "true", "display.on.consent.screen": "false"}
        for name in SSF_SCOPES:
            scope = self.admin.get_client_scope_by_name(name)
            if scope is None:
                self.admin.create_client_scope(
                    {"name": name, "protocol": "openid-connect", "attributes": wanted},
                    skip_exists=True,
                )
                self.report(f"Created the client scope {name!r}.")
                continue
            attributes = scope.get("attributes") or {}
            if attributes.get("include.in.token.scope") != "true":
                scope["attributes"] = {**attributes, "include.in.token.scope": "true"}
                self.admin.update_client_scope(scope["id"], scope)
                self.report(f"Included the client scope {name!r} in the token scope.")

    def ensure_client(self, client_id: str) -> str:
        client_uuid: str | None = self.admin.get_client_id(client_id)
        if client_uuid is None:
            self.admin.create_client(client_representation(client_id), skip_exists=True)
            client_uuid = self.admin.get_client_id(client_id)
            if client_uuid is None:
                msg = f"Keycloak didn't create the client {client_id!r}."
                raise KeycloakSetupError(msg)
            self.report(f"Created the client {client_id!r}.")
            return client_uuid
        current = self.admin.get_client(client_uuid)
        wanted = client_representation(client_id, current)
        if wanted != current:
            self.admin.update_client(client_uuid, wanted)
            self.report(f"Updated the client {client_id!r}.")
        return client_uuid

    def ensure_default_scopes(self, client_uuid: str) -> None:
        """
        Make the SSF scopes and ``offline_access`` default scopes of the client.

        Keycloak attaches ``offline_access`` to a new client as an optional
        scope, and an optional scope doesn't become a default one by adding it
        again, so it is detached first.
        """
        present = {scope["name"] for scope in self.admin.get_client_default_client_scopes(client_uuid)}
        optional = {
            scope["name"]: scope["id"]
            for scope in self.admin.get_client_optional_client_scopes(client_uuid)
        }
        for name in DEFAULT_CLIENT_SCOPES:
            if name in present:
                continue
            scope = self.admin.get_client_scope_by_name(name)
            if scope is None:
                msg = f"The realm {self.realm!r} has no client scope {name!r}."
                raise KeycloakSetupError(msg)
            if name in optional:
                self.admin.delete_client_optional_client_scope(client_uuid, optional[name])
            self.admin.add_client_default_client_scope(
                client_uuid,
                scope["id"],
                {"realm": self.realm, "client": client_uuid, "clientScopeId": scope["id"]},
            )
            self.report(f"Added {name!r} to the default client scopes.")
        present = {scope["name"] for scope in self.admin.get_client_default_client_scopes(client_uuid)}
        missing = [name for name in DEFAULT_CLIENT_SCOPES if name not in present]
        if missing:
            msg = f"Keycloak didn't add {', '.join(missing)} to the default client scopes."
            raise KeycloakSetupError(msg)

    def ensure_role(self, client_uuid: str) -> dict[str, Any]:
        self.admin.create_client_role(client_uuid, {"name": SSF_ADMIN_ROLE}, skip_exists=True)
        role: dict[str, Any] = self.admin.get_client_role(client_uuid, SSF_ADMIN_ROLE)
        return role

    def ensure_user(
        self,
        user: AdminUser,
        client_uuid: str,
        role: dict[str, Any],
        ask_password: Callable[[], str],
    ) -> None:
        user_id = self.admin.get_user_id(user.username)
        if user_id is not None:
            if self.admin.get_user(user_id).get("federationLink"):
                msg = (
                    f"The user {user.username!r} comes from UCS, and Keycloak can't assign "
                    "client roles to it. Choose a user name that doesn't exist in UCS."
                )
                raise KeycloakSetupError(msg)
            self.report(f"Keeping the existing user {user.username!r} and its password.")
        else:
            self.admin.create_user(
                {
                    "username": user.username,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                    "email": user.email,
                    "emailVerified": True,
                    "enabled": True,
                },
                exist_ok=False,
            )
            user_id = self.admin.get_user_id(user.username)
            if user_id is None:
                msg = f"Keycloak didn't create the user {user.username!r}."
                raise KeycloakSetupError(msg)
            self.admin.set_user_password(user_id, ask_password(), temporary=False)
            self.report(f"Created the user {user.username!r}.")
        roles = {
            granted["name"] for granted in self.admin.get_client_roles_of_user(user_id, client_uuid)
        }
        if SSF_ADMIN_ROLE not in roles:
            self.admin.assign_client_role(user_id, client_uuid, [role])
            self.report(f"Assigned the client role {SSF_ADMIN_ROLE!r} to {user.username!r}.")
