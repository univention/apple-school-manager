# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only

"""
Univention Apple School Manager Connector.

Configuration of the Apple School Manager accounts, the settings of the users
per account and the settings of the classes per school.
"""

import json
import logging
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from univention.config_registry import ConfigRegistry, handler_unset

CONFIG_FILE_PATH = "/etc/asm-connections.json"
LEGACY_PASSWORD_FILE_PATH = "/etc/asm.secret"  # noqa: S105
MIGRATED_ACCOUNT_NAME = "default"
OTHER_SCHOOLS = "*"
PASSWORD_POLICIES = (4, 6, 8)
ANONYMIZE_ATTRIBUTES = ("first_name", "middle_name", "last_name", "email_address", "sis_username")
REQUIRED_ANONYMIZE_ATTRIBUTES = ("first_name", "last_name")
DEFAULT_ANONYMIZE_VALUES: Mapping[str, str | None] = MappingProxyType(
    {
        "first_name": "%uid",
        "middle_name": None,
        "last_name": "-",
        "email_address": None,
        "sis_username": "%uid",
    },
)

_OPTIONAL_STR = (str, type(None))
_OPTIONAL_INT = (int, type(None))
_ROLE_SPEC: dict[str, Any] = {
    "anonymize": bool,
    "anonymize_values": dict.fromkeys(ANONYMIZE_ATTRIBUTES, _OPTIONAL_STR),
    "person_id_attribute": str,
}
ACCOUNT_SETTINGS_SPEC: dict[str, Any] = {
    "email_prepend_domain": str,
    "student": {**_ROLE_SPEC, "password_policy": _OPTIONAL_INT, "grade_level_attribute": _OPTIONAL_STR},
    "staff": _ROLE_SPEC,
}
SCHOOL_SETTINGS_SPEC: dict[str, Any] = {
    "course_name_pattern": str,
    "class_number_empty": bool,
    "student": {"ldap_filter": str},
    "staff": {"ldap_filter": str},
}
ACCOUNT_SPEC: dict[str, Any] = {"username": str, "password_file": str, **ACCOUNT_SETTINGS_SPEC}
SCHOOL_SPEC: dict[str, Any] = {"account": str, **SCHOOL_SETTINGS_SPEC}
DEFAULTS_SPEC: dict[str, Any] = {
    **ACCOUNT_SETTINGS_SPEC,
    **SCHOOL_SETTINGS_SPEC,
    "student": {**ACCOUNT_SETTINGS_SPEC["student"], **SCHOOL_SETTINGS_SPEC["student"]},
    "staff": {**ACCOUNT_SETTINGS_SPEC["staff"], **SCHOOL_SETTINGS_SPEC["staff"]},
}


class ASMConfigError(Exception):
    pass


@dataclass(frozen=True)
class RoleSettings:
    anonymize: bool = True
    anonymize_values: Mapping[str, str | None] = field(default_factory=lambda: DEFAULT_ANONYMIZE_VALUES)
    person_id_attribute: str = "entryUUID"


@dataclass(frozen=True)
class StudentSettings(RoleSettings):
    password_policy: int | None = 4
    grade_level_attribute: str | None = None


@dataclass(frozen=True)
class SchoolSettings:
    course_name_pattern: str = "{ou}-{name}"
    class_number_empty: bool = True
    student_ldap_filter: str = ""
    staff_ldap_filter: str = ""


@dataclass(frozen=True)
class Settings:
    """
    Everything that decides what one Apple School Manager account receives.

    The default instance covers every school with the built-in defaults.
    """

    email_prepend_domain: str = ""
    student: StudentSettings = field(default_factory=StudentSettings)
    staff: RoleSettings = field(default_factory=RoleSettings)
    schools: Mapping[str, SchoolSettings] = field(default_factory=dict)
    other_schools: SchoolSettings | None = field(default_factory=SchoolSettings)
    excluded_schools: frozenset[str] = frozenset()

    def includes(self, school: str) -> bool:
        """Whether the account receives `school`."""
        if school in self.schools:
            return True
        return self.other_schools is not None and school not in self.excluded_schools

    def school(self, school: str) -> SchoolSettings:
        """
        Return the settings of `school`.

        :raises ValueError: if the account doesn't receive `school`
        """
        if school in self.schools:
            return self.schools[school]
        if self.other_schools is not None and school not in self.excluded_schools:
            return self.other_schools
        msg = f"School {school!r} is not synchronized to this Apple School Manager account."
        raise ValueError(msg)


@dataclass(frozen=True)
class Connection:
    name: str
    username: str
    password: str
    settings: Settings


def get_connections() -> list[Connection]:
    """
    Return the Apple School Manager connections from :py:data:`CONFIG_FILE_PATH`.

    :raises ASMConfigError: if the file is missing, incomplete or invalid
    """
    if not os.path.exists(CONFIG_FILE_PATH):
        msg = (
            f"No Apple School Manager account configured. Create {CONFIG_FILE_PATH} "
            "as described in the Apple School Manager Connector manual."
        )
        raise ASMConfigError(msg)
    try:
        with open(CONFIG_FILE_PATH) as config_file:
            data = json.load(config_file)
    except json.JSONDecodeError as exc:
        msg = f"Config file {CONFIG_FILE_PATH!r} is not valid JSON: {exc}"
        raise ASMConfigError(msg)
    return parse_config(data, CONFIG_FILE_PATH)


def parse_config(data: Any, source: str = "configuration") -> list[Connection]:  # noqa: ANN401
    """
    Validate the content of the configuration file and build the connections.

    :param data: the decoded JSON content
    :param source: name of the file, for error messages
    :raises ASMConfigError: if the configuration is incomplete or invalid
    """
    if not isinstance(data, dict):
        msg = f"{source} must contain a JSON object."
        raise ASMConfigError(msg)
    _check_keys(data, {"accounts", "defaults", "schools"}, source)
    accounts = data.get("accounts", {})
    schools = data.get("schools", {})
    defaults = data.get("defaults", {})
    _check(defaults, DEFAULTS_SPEC, f"{source}: defaults")
    _check_entries(accounts, ACCOUNT_SPEC, source, "account")
    _check_entries(schools, SCHOOL_SPEC, source, "school")
    if not accounts:
        msg = f"No Apple School Manager account configured in {source}."
        raise ASMConfigError(msg)
    if not schools:
        msg = f"No school assigned to an Apple School Manager account in {source}."
        raise ASMConfigError(msg)
    for school, entry in schools.items():
        account = _required_str(entry, "account", f"{source}: school {school!r}")
        if account not in accounts:
            msg = f"{source}: school {school!r} refers to the unknown account {account!r}."
            raise ASMConfigError(msg)
    usernames = [entry.get("username") for entry in accounts.values()]
    duplicates = sorted({str(name) for name in usernames if usernames.count(name) > 1})
    if duplicates:
        msg = f"{source} lists the username(s) {', '.join(duplicates)} for more than one account."
        raise ASMConfigError(msg)

    logger = logging.getLogger(__name__)
    connections = []
    for name, account in accounts.items():
        where = f"{source}: account {name!r}"
        own_schools = {school: entry for school, entry in schools.items() if entry["account"] == name}
        if not own_schools:
            logger.warning("%s has no schools and receives no upload.", where)
            continue
        connections.append(
            Connection(
                name=name,
                username=_required_str(account, "username", where),
                password=_read_password(_required_str(account, "password_file", where), where),
                settings=_build_settings(name, account, defaults, own_schools, schools, source),
            ),
        )
    return connections


def check_schools(connections: Iterable[Connection], existing_schools: Iterable[str]) -> None:
    """
    Make sure that every school that the connections name exists.

    A misspelled school would otherwise go to the account of the entry ``*``
    instead of the account it was meant for.

    :param connections: the connections from :py:func:`get_connections`
    :param existing_schools: the names of the schools in LDAP
    :raises ASMConfigError: if a connection names a school that doesn't exist
    """
    named = {school for connection in connections for school in connection.settings.schools}
    unknown = sorted(named - set(existing_schools))
    if unknown:
        msg = (
            f"{CONFIG_FILE_PATH} lists the school(s) {', '.join(unknown)}, which don't exist. "
            "Correct or remove them."
        )
        raise ASMConfigError(msg)


def _build_settings(
    name: str,
    account: dict[str, Any],
    defaults: dict[str, Any],
    own_schools: dict[str, dict[str, Any]],
    all_schools: dict[str, dict[str, Any]],
    source: str,
) -> Settings:
    where = f"{source}: account {name!r}"
    user_data = _merge(
        _project(defaults, ACCOUNT_SETTINGS_SPEC), _project(account, ACCOUNT_SETTINGS_SPEC)
    )
    school_defaults = _project(defaults, SCHOOL_SETTINGS_SPEC)
    school_settings = {
        school: _school_settings(_merge(school_defaults, _project(entry, SCHOOL_SETTINGS_SPEC)))
        for school, entry in own_schools.items()
    }
    other_schools = school_settings.pop(OTHER_SCHOOLS, None)
    return Settings(
        email_prepend_domain=user_data.get("email_prepend_domain", "").strip(" ."),
        student=_student_settings(user_data.get("student", {}), f"{where}, student"),
        staff=_role_settings(user_data.get("staff", {}), f"{where}, staff"),
        schools=MappingProxyType(school_settings),
        other_schools=other_schools,
        excluded_schools=frozenset(school for school in all_schools if school != OTHER_SCHOOLS)
        - school_settings.keys(),
    )


def _role_settings(data: dict[str, Any], where: str) -> RoleSettings:
    return RoleSettings(**_role_kwargs(data, where))


def _student_settings(data: dict[str, Any], where: str) -> StudentSettings:
    default = StudentSettings()
    password_policy = data.get("password_policy", default.password_policy)
    if password_policy is not None and (
        isinstance(password_policy, bool) or password_policy not in PASSWORD_POLICIES
    ):
        msg = f"{where}: password_policy must be 4, 6, 8 or null, not {password_policy!r}."
        raise ASMConfigError(msg)
    return StudentSettings(
        **_role_kwargs(data, where),
        password_policy=password_policy,
        grade_level_attribute=data.get("grade_level_attribute") or None,
    )


def _role_kwargs(data: dict[str, Any], where: str) -> dict[str, Any]:
    default = RoleSettings()
    anonymize = data.get("anonymize", default.anonymize)
    anonymize_values = {**DEFAULT_ANONYMIZE_VALUES, **data.get("anonymize_values", {})}
    if anonymize:
        for attribute in REQUIRED_ANONYMIZE_ATTRIBUTES:
            if not anonymize_values[attribute]:
                msg = f"{where}: anonymize_values.{attribute} must not be empty."
                raise ASMConfigError(msg)
    person_id_attribute = data.get("person_id_attribute", default.person_id_attribute)
    if not person_id_attribute:
        msg = f"{where}: person_id_attribute must not be empty."
        raise ASMConfigError(msg)
    return {
        "anonymize": anonymize,
        "anonymize_values": MappingProxyType(anonymize_values),
        "person_id_attribute": person_id_attribute,
    }


def _school_settings(data: dict[str, Any]) -> SchoolSettings:
    default = SchoolSettings()
    return SchoolSettings(
        course_name_pattern=data.get("course_name_pattern", default.course_name_pattern),
        class_number_empty=data.get("class_number_empty", default.class_number_empty),
        student_ldap_filter=data.get("student", {}).get("ldap_filter", default.student_ldap_filter),
        staff_ldap_filter=data.get("staff", {}).get("ldap_filter", default.staff_ldap_filter),
    )


def _check_entries(entries: Any, spec: dict[str, Any], source: str, kind: str) -> None:  # noqa: ANN401
    if not isinstance(entries, dict):
        msg = f"{source}: {kind}s must be a JSON object."
        raise ASMConfigError(msg)
    for name, entry in entries.items():
        if not name:
            msg = f"{source}: {kind} names must not be empty."
            raise ASMConfigError(msg)
        _check(entry, spec, f"{source}: {kind} {name!r}")


def _check(value: Any, spec: Any, where: str) -> None:  # noqa: ANN401
    if isinstance(spec, dict):
        if not isinstance(value, dict):
            msg = f"{where} must be a JSON object."
            raise ASMConfigError(msg)
        _check_keys(value, spec.keys(), where)
        for key, sub_value in value.items():
            _check(sub_value, spec[key], f"{where}.{key}")
        return
    types = spec if isinstance(spec, tuple) else (spec,)
    if not isinstance(value, types) or (isinstance(value, bool) and bool not in types):
        names = " or ".join("null" if t is type(None) else t.__name__ for t in types)
        msg = f"{where} must be of type {names}, not {value!r}."
        raise ASMConfigError(msg)


def _check_keys(value: dict[str, Any], allowed: Any, where: str) -> None:  # noqa: ANN401
    unknown = value.keys() - set(allowed)
    if unknown:
        msg = f"{where} has unknown key(s) {', '.join(sorted(unknown))}."
        raise ASMConfigError(msg)


def _project(data: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Return the part of `data` that `spec` describes."""
    result: dict[str, Any] = {}
    for key, value in data.items():
        if key not in spec:
            continue
        if isinstance(spec[key], dict):
            result[key] = _project(value, spec[key])
        else:
            result[key] = value
    return result


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _required_str(entry: dict[str, Any], key: str, where: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        msg = f"{where}: {key} must be a non-empty string."
        raise ASMConfigError(msg)
    return value


def _read_password(path: str, where: str) -> str:
    try:
        with open(path) as password_file:
            password = password_file.read().strip("\n")
    except FileNotFoundError:
        msg = f"{where}: password file {path!r} does not exist."
        raise ASMConfigError(msg)
    if not password:
        msg = f"{where}: password file {path!r} is empty."
        raise ASMConfigError(msg)
    return password


def write_initial_config() -> bool:
    """
    Create :py:data:`CONFIG_FILE_PATH` from the former app settings and UCR variables.

    Does nothing if the file already exists. On a system without a former
    configuration, the file contains no account yet. Removes the UCR
    variables that it migrated. The password stays in
    :py:data:`LEGACY_PASSWORD_FILE_PATH`.

    :return: whether the file was created
    """
    if os.path.exists(CONFIG_FILE_PATH):
        return False
    ucr = ConfigRegistry()
    ucr.load()
    data, migrated_keys = config_from_ucr(ucr)
    fd = os.open(CONFIG_FILE_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as config_file:
        json.dump(data, config_file, indent=4)
        config_file.write("\n")
    if migrated_keys:
        handler_unset(sorted(migrated_keys))
        print(f"Migrated the Apple School Manager settings to {CONFIG_FILE_PATH}.")
    return True


def config_from_ucr(ucr: Mapping[str, str]) -> tuple[dict[str, Any], set[str]]:
    """
    Translate the former app settings and UCR variables into the file format.

    :param ucr: loaded UCR
    :return: the file content and the UCR variables that it replaces
    """
    migrated: set[str] = set()

    def take(key: str) -> str | None:
        value = ucr.get(key)
        if value is None:
            return None
        migrated.add(key)
        return value

    defaults: dict[str, Any] = {}
    student: dict[str, Any] = {}
    staff: dict[str, Any] = {}
    if (value := take("asm/attributes/user/email/prepend_domain")) is not None:
        defaults["email_prepend_domain"] = value
    for role, target in (("student", student), ("staff", staff)):
        if (value := take(f"asm/attributes/{role}/anonymize")) is not None:
            target["anonymize"] = _is_true(value)
        anonymize_values = {}
        for attribute in ANONYMIZE_ATTRIBUTES:
            if (value := take(f"asm/attributes/{role}/anonymize/{attribute}")) is not None:
                anonymize_values[attribute] = value or None
        if anonymize_values:
            target["anonymize_values"] = anonymize_values
        if (value := take(f"asm/attributes/{role}/person_id/mapping")) is not None:
            target["person_id_attribute"] = value.strip().removeprefix("%").strip()
    if (value := take("asm/attributes/student/password_policy")) is not None:
        student["password_policy"] = None if value.strip() == "-" else _int_or_str(value)
    if (value := take("asm/attributes/student/grade_level")) is not None:
        student["grade_level_attribute"] = value or None
    if (value := take("asm/attributes/course-name-pattern")) is not None:
        defaults["course_name_pattern"] = value
    if (value := take("asm/attributes/classes/class_number_empty")) is not None:
        defaults["class_number_empty"] = _is_true(value)
    if (value := take("asm/ldap_filter/students")) is not None:
        student["ldap_filter"] = value
    if (value := take("asm/ldap_filter/staff")) is not None:
        staff["ldap_filter"] = value
    if student:
        defaults["student"] = student
    if staff:
        defaults["staff"] = staff

    accounts: dict[str, Any] = {}
    schools: dict[str, Any] = {}
    username = take("asm/username")
    if username:
        accounts[MIGRATED_ACCOUNT_NAME] = {
            "username": username,
            "password_file": LEGACY_PASSWORD_FILE_PATH,
        }
        whitelist = [school.strip() for school in (take("asm/school_whitelist") or "").split(",")]
        for school in [school for school in whitelist if school] or [OTHER_SCHOOLS]:
            schools[school] = {"account": MIGRATED_ACCOUNT_NAME}
    elif ucr.get("asm/school_whitelist"):
        print("Keeping asm/school_whitelist: asm/username is not set, so there is no account for it.")
    else:
        take("asm/school_whitelist")

    for key in sorted(ucr.keys()):
        for role, prefix in (
            ("student", "asm/ldap_filter/students/"),
            ("staff", "asm/ldap_filter/staff/"),
        ):
            if not key.startswith(prefix):
                continue
            school = key.removeprefix(prefix)
            if not username:
                print(f"Keeping {key}: asm/username is not set, so there is no account for it.")
                continue
            if school not in schools and OTHER_SCHOOLS not in schools:
                print(f"Dropping {key}: school {school!r} is not synchronized.")
                migrated.add(key)
                continue
            entry = schools.setdefault(school, {"account": MIGRATED_ACCOUNT_NAME})
            entry.setdefault(role, {})["ldap_filter"] = take(key)

    return {"accounts": accounts, "defaults": defaults, "schools": schools}, migrated


def _is_true(value: str) -> bool:
    return value.strip().lower() in ("yes", "true", "1", "enable", "enabled", "on")


def _int_or_str(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value
