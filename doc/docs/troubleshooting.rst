.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _troubleshooting:

***************
Troubleshooting
***************

This chapter describes where the connector logs its activity
and what to do about the problems that occur most often.

.. _troubleshooting-log:

Log file
========

The connector writes log information to the :file:`/var/log/univention/asm.log` log file.
The file holds the debug-level log of every run,
including the teachers whom an LDAP filter excluded from a class.

For the timestamp of the most recent upload to any account,
check :envvar:`asm/last_upload` in the app settings.
For instructions, see :ref:`configuration-app-settings`.

For the timestamp of the most recent upload to a specific account,
check :envvar:`asm/last_upload/ACCOUNT`.
Replace ``ACCOUNT`` with the account name
from the :envvar:`accounts` section of the settings file.

The connector uses the system's ``logrotate/*`` UCR variables for log rotation.
Its log rotation configuration is in :file:`/etc/logrotate.d/asm`.

To follow a synchronization run in the log file,
use the command in :numref:`troubleshooting-log-listing`.

.. code-block:: console
   :caption: Follow a synchronization run
   :name: troubleshooting-log-listing

   $ tail -f /var/log/univention/asm.log

.. _troubleshooting-apple-messages:

Get better error messages from Apple School Manager
===================================================

*Apple School Manager* provides limited information
about errors in uploaded data.
The page that shows the SFTP credentials gives more details
about the data that *Apple School Manager* rejects.
To view these details during an upload, follow these steps:

#. Open the page with the SFTP credentials in *Apple School Manager*,
   as described in :ref:`installation-credentials`.

#. Keep the page open
   and start a synchronization run,
   as described in :ref:`synchronization-run`.

The page shows errors for each upload while it runs.

.. _troubleshooting-users-missing:

Users don't appear in Apple School Manager
==========================================

.. FIXME: Add verified diagnostic and corrective actions for each cause.
   Clarify how to check and set a user's primary email address,
   then explain how to retry the affected upload
   and verify that the user appears in Apple School Manager.

If user accounts don't appear in *Apple School Manager*,
check the following possible causes in the listed order:

#. **The user has no primary email address.**

   The connector exports the user without an email address,
   and *Apple School Manager* can't create an *Apple Account* for the user.

#. **Anonymization removed the email address.**

   The connector has anonymization enabled by default.
   If the account has :envvar:`student.anonymize` or :envvar:`staff.anonymize` enabled,
   the connector exports a replacement value instead of the email address.
   The default email replacement value is empty.
   For more information, see :ref:`configuration-anonymization`.

   To deactivate anonymization by default for both students and staff,
   add the settings in :numref:`troubleshooting-users-missing-anonymization-listing`
   to the existing configuration.
   Account-specific settings can override these defaults.
   Without anonymization, the connector exports the original attribute values,
   including names and email addresses.
   For account-specific settings, see :ref:`configuration-anonymization`.

   .. code-block:: json
      :caption: Turn anonymization off in :file:`/etc/asm-connections.json`
      :name: troubleshooting-users-missing-anonymization-listing

      "defaults": {
          "student": {"anonymize": false},
          "staff": {"anonymize": false}
      }

#. **The school isn't on the list.**

   The connector exports only schools
   that the :envvar:`schools` section of the settings file lists.
   It exports each school only to the account assigned to that school.
   For more information,
   see :ref:`configuration-school-list`.

#. **An LDAP filter excludes the user.**

   The log file doesn't name users whom a filter excluded.
   Run the filter with :command:`univention-ldapsearch`
   to check which users it selects.
   For more information,
   see :ref:`configuration-ldap-filter`.

   .. FIXME: Clarify with the team which LDAP-filter exclusions the log names.
      This sentence says that the log doesn't name excluded users,
      but the log file and class troubleshooting sections say that it records
      teachers excluded from a class.

.. _troubleshooting-no-students:

Apple School Manager rejects an upload without students
=======================================================

*Apple School Manager* rejects an upload
that contains no students and shows an error.
Every account needs at least one student in its upload.

.. FIXME: Add verified recovery steps for an upload without students.
   Clarify how to make an eligible student available to the account
   or correct the LDAP filter, then retry the upload and verify its result.

An upload contains no students in the following cases:

* None of the schools assigned to the account has a student.

* The LDAP filter for students excludes every student of those schools.
  For more information, see :ref:`configuration-ldap-filter`.

To see the error,
follow the instructions in :ref:`troubleshooting-apple-messages`.

.. _troubleshooting-credentials:

The run stops with a credential error
=====================================

The connector stops before it collects any data
if :file:`/etc/asm-connections.json` is missing or invalid,
or if a password file is missing or empty.
The message in the log names the file and the entry,
as shown in the example in :numref:`troubleshooting-credentials-listing`.

Configure the accounts and their password files,
as described in :ref:`configuration-accounts`.
If Apple rejects the credentials,
generate new credentials in *Apple School Manager*
and configure them as described in :ref:`configuration-accounts`.

After correcting the configuration,
run the synchronization again as described in :ref:`synchronization-run`.
Check the log file for errors and the timestamp of the last upload,
as described in :ref:`troubleshooting-log`.

.. code-block:: text
   :caption: Message in the log file
   :name: troubleshooting-credentials-listing

   No *Apple School Manager* account configured. Create /etc/asm-connections.json as described in the Apple School Manager Connector manual.

.. _troubleshooting-host-key:

The upload stops with a missing host key
========================================

The connector verifies the host key of the SFTP server against
:file:`/etc/asm_public_key`.
The *Apple School Manager Connector* ships that file.
If it's missing or no longer matches the server,
the upload fails with the message ``Could not find /etc/asm_public_key``
or with an SSH exception.

.. FIXME: Add a verified procedure or link for reinstalling
   the univention-apple-school-manager-connector package,
   including the required privileges.

If the file is missing, reinstall the package to restore it.
If Apple changed the host key,
report the change to Univention
so that an update of the app can ship the new key.
For support options, see :ref:`troubleshooting-support`.

.. _troubleshooting-ldap-filter:

The upload to an account stops with an invalid LDAP filter
==========================================================

An LDAP filter with a syntax error stops the upload
to the account of the school that has the filter.
The connector still uploads to the remaining accounts
and exits with a non-zero status at the end.
The log file lists the filter and the account,
as shown in the example in :numref:`troubleshooting-ldap-filter-listing`.

Correct the filter in the settings file,
or remove the ``ldap_filter`` key from the school's ``student`` or ``staff`` settings
to fall back to the filter in :envvar:`defaults`.
For more information, see :ref:`configuration-ldap-filter`.

After correcting the filter,
run the synchronization again as described in :ref:`synchronization-run`.
Check the log file for errors and the last-upload timestamp for the affected account,
as described in :ref:`troubleshooting-log`.

.. code-block:: text
   :caption: Messages in the log file
   :name: troubleshooting-ldap-filter-listing

   Invalid LDAP-filter for students: '(ucsschoolRole=student'
   Invalid LDAP filter, nothing uploaded to account north.

.. _troubleshooting-no-csv:

Classes have fewer teachers than expected
=========================================

.. FIXME: Add verified diagnostic and corrective guidance for classes
   with fewer teachers than expected.
   Clarify how to identify the exported teachers, address the 15-teacher limit,
   investigate LDAP-filter exclusions, and verify the result.

*Apple School Manager* supports at most 15 teachers per class.
The connector exports the first 15
and writes a warning that names the class to the log file.
This is a limitation of *Apple School Manager*,
not of the connector.

An LDAP filter for teachers can also reduce the number.
The log file records every teacher whom a filter excluded from a class.

.. _troubleshooting-federation-again:

Federation for a domain fails the second time
=============================================

If you deactivate federation for a domain and then enable it again,
*Apple School Manager* shows an error.

While federation is active,
*Apple School Manager* offers to disconnect the domain instead of removing it.
Disconnecting removes the domain from the federation,
but the domain stays in *Apple School Manager*.

.. FIXME: Clarify the starting state for this recovery procedure.
   The preceding paragraph describes disconnecting the domain from federation,
   but the first step says to disconnect the identity provider.
   Ask the team how these actions relate and whether both are required.

To enable federation for the domain again,
follow these steps:

#. In *Apple School Manager*,
   disconnect the identity provider.

#. Connect it again,
   as described in :ref:`identity-provider-asm-idp`.

#. Enable federation for the domain,
   as described in :ref:`identity-provider-asm-domain`.

.. _troubleshooting-support:

Where to get help
=================

You can ask for help through the following channels:

* The `Univention Help <https://help.univention.com/>`_ forum
  for community support.

* Your Univention support contract for a supported environment.

When you report a problem,
attach the relevant part of :file:`/var/log/univention/asm.log`.
Before sharing the excerpt,
check it for sensitive personal information and credentials.
Remove sensitive information, but keep the details needed to diagnose the problem.
