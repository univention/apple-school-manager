#!/bin/bash
# SPDX-FileCopyrightText: 2026 Univention GmbH
# SPDX-License-Identifier: AGPL-3.0-only
#
# Set up a UCS@school Primary Directory Node with the Apple School Manager
# Connector 5.1.1 and every setting it supports, as a source system for
# testing the update to 5.2.0 and its settings migration.
# The users, classes and work groups are provisioned with the Kelvin REST API.
#
# Run as root on the VM. Fill in the credentials below or pass them as
# environment variables:
#
#   ASM_USERNAME=... ASM_PASSWORD=... ./setup-asm-5.1.1-vm.sh
#
# Saving the app settings at the end triggers one upload to Apple School
# Manager (asm/run_on_appsetting_save). Use a test account.

set -euo pipefail

# --- Credentials (required) --------------------------------------------------
ASM_USERNAME="${ASM_USERNAME:-INSERT_SFTP_USERNAME}"
ASM_PASSWORD="${ASM_PASSWORD:-INSERT_SFTP_PASSWORD}"

# --- Domain administrator for the app installation and Kelvin ----------------
ADMIN_USER="${ADMIN_USER:-Administrator}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-univention}"

# --- Test data ----------------------------------------------------------------
APP_VERSION="${APP_VERSION:-5.1.1}"
# SCHOOL_1 and SCHOOL_2 go on asm/school_whitelist, SCHOOL_3 doesn't.
SCHOOL_1="${SCHOOL_1:-asm1}"
SCHOOL_2="${SCHOOL_2:-asm2}"
SCHOOL_3="${SCHOOL_3:-asm3}"
# Password of the test users; must satisfy the password policy of the domain.
USER_PASSWORD="${USER_PASSWORD:-univention-asm-test}"

KELVIN_APP="ucsschool-kelvin-rest-api"
KELVIN_UDM_MAPPING="/etc/ucsschool/kelvin/mapped_udm_properties.json"

die () { echo "ERROR: $*" >&2; exit 1; }
step () { echo; echo "=== $*"; }
app_installed () { [ "$(ucr get "appcenter/apps/$1/status")" = "installed" ]; }

[ "$(id -u)" -eq 0 ] || die "Run this script as root."
case "$ASM_USERNAME$ASM_PASSWORD" in
	*INSERT_SFTP_*) die "Set ASM_USERNAME and ASM_PASSWORD." ;;
esac
[ "$(ucr get server/role)" = "domaincontroller_master" ] || die "Run this script on the Primary Directory Node."
app_installed ucsschool || die "UCS@school isn't installed."

eval "$(ucr shell ldap/base hostname domainname)"
MAIL_DOMAIN="$domainname"
FQDN="$hostname.$domainname"

pwdfile="$(mktemp)"
trap 'rm -f "$pwdfile"' EXIT
printf '%s' "$ADMIN_PASSWORD" >"$pwdfile"

step "Install apple-school-manager=$APP_VERSION"
if [ "$(ucr get appcenter/apps/apple-school-manager/version)" = "$APP_VERSION" ] && app_installed apple-school-manager; then
	echo "Already installed."
else
	univention-app install "apple-school-manager=$APP_VERSION" \
		--noninteractive --username "$ADMIN_USER" --pwdfile "$pwdfile"
fi

step "Install $KELVIN_APP"
if app_installed "$KELVIN_APP"; then
	echo "Already installed."
else
	univention-app install "$KELVIN_APP" \
		--noninteractive --username "$ADMIN_USER" --pwdfile "$pwdfile"
fi

step "Map the UDM properties employeeNumber and initials in Kelvin"
# employeeNumber holds the grade level, initials the middle name.
mapping_changed="$(python3 - "$KELVIN_UDM_MAPPING" <<'EOF'
import json, os, sys

path = sys.argv[1]
wanted = ["employeeNumber", "initials"]
config = {}
if os.path.exists(path):
    with open(path) as fd:
        config = json.load(fd)
missing = [prop for prop in wanted if prop not in config.get("user", [])]
if not missing:
    print("no")
    sys.exit(0)
config.setdefault("user", []).extend(missing)
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as fd:
    json.dump(config, fd, indent=4)
print("yes")
EOF
)"
if [ "$mapping_changed" = "yes" ]; then
	univention-app restart "$KELVIN_APP"
else
	echo "Already mapped."
fi

step "Create the mail domain $MAIL_DOMAIN"
udm mail/domain create --ignore_exists \
	--position "cn=domain,cn=mail,$ldap_base" \
	--set name="$MAIL_DOMAIN"

step "Create the schools $SCHOOL_1, $SCHOOL_2, $SCHOOL_3"
for school in "$SCHOOL_1" "$SCHOOL_2" "$SCHOOL_3"; do
	if [ -n "$(univention-ldapsearch -LLL -b "$ldap_base" "(&(objectClass=ucsschoolOrganizationalUnit)(ou=$school))" dn)" ]; then
		echo "$school exists."
	else
		/usr/share/ucs-school-import/scripts/create_ou "$school"
	fi
done

step "Create classes, work groups, teachers and students with Kelvin"
python3 - "$FQDN" "$ADMIN_USER" "$pwdfile" "$USER_PASSWORD" "$MAIL_DOMAIN" "$SCHOOL_1" "$SCHOOL_2" "$SCHOOL_3" <<'EOF'
import sys
import time

import requests

fqdn, admin_user, pwdfile, user_password, mail_domain, school_1, school_2, school_3 = sys.argv[1:]
schools = (school_1, school_2, school_3)
base = f"https://{fqdn}/ucsschool/kelvin"
api = f"{base}/v1"
session = requests.Session()
session.verify = "/etc/univention/ssl/ucsCA/CAcert.pem"

with open(pwdfile) as fd:
    admin_password = fd.read()

# Kelvin may still be starting after an installation or restart.
for _ in range(60):
    try:
        resp = session.post(f"{base}/token", data={"username": admin_user, "password": admin_password})
    except requests.ConnectionError:
        resp = None
    if resp is not None and resp.status_code == 200:
        break
    time.sleep(5)
else:
    sys.exit(f"Kelvin doesn't hand out a token: {resp.status_code if resp else 'no connection'} {resp.text if resp else ''}")
session.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"


def school_url(school):
    return f"{api}/schools/{school}"


def role_url(role):
    return f"{api}/roles/{role}"


def ensure(resource, get_path, body, update=()):
    """
    Create the object unless GET on `get_path` finds it.

    An existing object gets the keys `update` of `body` patched in,
    so a rerun fixes data from an earlier version of this script.
    """
    if session.get(f"{api}/{resource}/{get_path}").status_code == 200:
        patch = {key: body[key] for key in update if key in body}
        if patch:
            resp = session.patch(f"{api}/{resource}/{get_path}", json=patch)
            if resp.status_code != 200:
                sys.exit(f"Updating {resource}/{get_path} failed: {resp.status_code} {resp.text}")
        print(f"{resource}/{get_path} exists.")
        return
    resp = session.post(f"{api}/{resource}/", json=body)
    if resp.status_code != 201:
        sys.exit(f"Creating {resource}/{get_path} failed: {resp.status_code} {resp.text}")
    print(f"Created {resource}/{get_path}.")


def user(name, role, user_schools, classes, workgroups=None, email=True, grade=None):
    body = {
        "name": name,
        "firstname": name.split("-")[0].capitalize(),
        "lastname": name,
        "school": school_url(user_schools[0]),
        "schools": [school_url(s) for s in user_schools],
        "roles": [role_url(role)],
        "password": user_password,
        "record_uid": name,
        "source_uid": "asm-test",
        "school_classes": classes,
        "workgroups": workgroups or {},
    }
    if email:
        body["email"] = f"{name}@{mail_domain}"
    if grade:
        body["udm_properties"] = {"employeeNumber": grade, "initials": "M."}
    ensure("users", name, body, update=("email",))


for school in schools:
    for name in ("1a", "2b"):
        ensure("classes", f"{school}/{name}", {"name": name, "school": school_url(school)})
    ensure("workgroups", f"{school}/wg1", {"name": "wg1", "school": school_url(school)})

for school in schools:
    for i in range(1, 4):
        user(
            f"stud-{school}-{i}", "student", [school],
            {school: ["1a" if i < 3 else "2b"]},
            {school: ["wg1"]} if i == 1 else None,
            # In SCHOOL_1, every second student has no email address and is
            # skipped by the (mailPrimaryAddress=*) filter. Everywhere else,
            # students need one: anonymization uses %mailPrimaryAddress,
            # which 5.1.1 requires on every exported student.
            email=bool(i % 2) or school != school_1,
            grade=str(6 + i),
        )
    for i in range(1, 3):
        user(
            f"teach-{school}-{i}", "teacher", [school],
            {school: ["1a"]},
            {school: ["wg1"]} if i == 1 else None,
        )

# Users in several schools: one in two whitelisted schools,
# one in a whitelisted and a non-whitelisted school.
user("stud-multi-12", "student", [school_1, school_2],
     {school_1: ["1a"], school_2: ["1a"]}, grade="9")
user("teach-multi-13", "teacher", [school_1, school_3],
     {school_1: ["2b"], school_3: ["2b"]}, {school_3: ["wg1"]})
# Excluded by the global student LDAP filter. SCHOOL_1 has its own filter,
# which replaces the global one, so this user is in SCHOOL_2.
user(f"excluded-{school_2}", "student", [school_2], {school_2: ["1a"]})
EOF

step "Set the UCR variables"
ucr set \
	asm/attributes/user/email/prepend_domain="apple" \
	asm/attributes/classes/class_number_empty="false" \
	asm/attributes/course-name-pattern="{ou} {name}" \
	asm/attributes/staff/anonymize="false" \
	asm/attributes/staff/anonymize/first_name="%uid" \
	asm/attributes/staff/anonymize/middle_name="" \
	asm/attributes/staff/anonymize/last_name="Teacher" \
	asm/attributes/staff/anonymize/email_address="" \
	asm/attributes/staff/anonymize/sis_username="%uid" \
	asm/attributes/staff/person_id/mapping="%entryUUID" \
	asm/attributes/student/anonymize="true" \
	asm/attributes/student/anonymize/first_name="%uid" \
	asm/attributes/student/anonymize/middle_name="X" \
	asm/attributes/student/anonymize/last_name="Student" \
	asm/attributes/student/anonymize/email_address="%mailPrimaryAddress" \
	asm/attributes/student/anonymize/sis_username="%uid" \
	asm/attributes/student/person_id/mapping="%entryUUID" \
	asm/attributes/student/password_policy="6" \
	asm/attributes/student/grade_level="employeeNumber" \
	asm/ldap_filter/students="(!(uid=excluded-*))" \
	asm/ldap_filter/staff="(uid=teach-*)" \
	"asm/ldap_filter/students/$SCHOOL_1=(mailPrimaryAddress=*)" \
	"asm/ldap_filter/staff/$SCHOOL_2=(uid=teach-$SCHOOL_2-1)" \
	"asm/ldap_filter/students/$SCHOOL_3=(uid=*)"
# The last filter belongs to a school that isn't on the whitelist;
# the 5.2.0 migration drops it.

step "Set the app settings (triggers one upload)"
univention-app configure apple-school-manager --set \
	asm/username="$ASM_USERNAME" \
	asm/password="$ASM_PASSWORD" \
	asm/school_whitelist="$SCHOOL_1,$SCHOOL_2" \
	asm/store_zip="True" \
	asm/sync_daily="True" \
	asm/sync_daily/hour="3" \
	asm/run_on_appsetting_save="True"

step "Result"
echo "apple-school-manager $(ucr get appcenter/apps/apple-school-manager/version)"
ucr search --brief '^asm/' | grep -v '^asm/password'
ls -l /etc/asm.secret /etc/cron.d/asm* 2>/dev/null || true
ls -l /var/lib/asm/ 2>/dev/null || true
echo
echo "Log: /var/log/univention/asm.log"
