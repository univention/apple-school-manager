.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _troubleshooting:

***************
Troubleshooting
***************

This chapter describes where the connector records what it does
and what to do about the problems that occur most often.

.. _troubleshooting-log:

Log file
========

The connector writes to :file:`/var/log/univention/asm.log`.
The file holds the debug-level log of every run,
including the teachers whom an LDAP filter excluded from a class.
The app settings show the time of the last upload in ``asm/last_upload``.
``asm/last_upload/ACCOUNT`` holds the time of the last upload to each account.

The log rotation follows the ``logrotate/*`` UCR variables of the system.
The connector writes its own configuration to :file:`/etc/logrotate.d/asm`.

.. code-block:: console
   :caption: Follow a synchronization run

   $ tail -f /var/log/univention/asm.log

.. _troubleshooting-apple-messages:

Get better error messages from Apple School Manager
===================================================

Apple School Manager reports errors in the uploaded data sparsely.
The page that shows the SFTP credentials gives more details
about the data that Apple School Manager rejects.
You can keep the SFTP upload connected.

#. Open the page with the SFTP credentials,
   as described in :ref:`installation-credentials`.

#. Keep the page open
   and start a synchronization run,
   as described in :ref:`synchronization-run`.

The page shows the errors of each upload while the upload runs.

.. _troubleshooting-users-missing:

Users don't appear in Apple School Manager
==========================================

Check the following, in this order:

#. **The user has no primary email address.**
   The connector exports the user without an email address,
   and Apple School Manager can't create an Apple Account for the user.

#. **Anonymization removed the email address.**
   Anonymization is enabled by default.
   With ``student.anonymize`` or ``staff.anonymize`` enabled for the account,
   the connector exports the replacement value instead of the address,
   which is empty by default.
   See :ref:`configuration-anonymization`.

   .. code-block:: json
      :caption: Turn anonymization off in :file:`/etc/asm-connections.json`

      "defaults": {
          "student": {"anonymize": false},
          "staff": {"anonymize": false}
      }

#. **The school isn't on the list.**
   The connector only exports schools that the ``schools`` section of the
   settings file lists,
   and only to the account that the school refers to.
   See :ref:`configuration-school-list`.

#. **An LDAP filter excludes the user.**
   The log file doesn't name users whom a filter excluded.
   Run the filter with :command:`univention-ldapsearch`
   to check which users it selects.
   See :ref:`configuration-ldap-filter`.

.. _troubleshooting-no-students:

Apple School Manager rejects an upload without students
=======================================================

Apple School Manager rejects an upload that contains no student
and shows an error.
Every account needs at least one student in its upload.

An upload contains no students in the following cases:

* None of the schools that the account receives has a student.

* The LDAP filter for students excludes every student of those schools.
  See :ref:`configuration-ldap-filter`.

To see the error,
follow :ref:`troubleshooting-apple-messages`.

.. _troubleshooting-credentials:

The run stops with a credential error
=====================================

The connector stops before it collects any data
if :file:`/etc/asm-connections.json` is missing or invalid,
or if a password file is missing or empty.
The message in the log file names the file and the entry.

.. code-block:: text
   :caption: Message in the log file

   No Apple School Manager account configured. Create /etc/asm-connections.json as described in the Apple School Manager Connector manual.

Configure the accounts,
as described in :ref:`configuration-accounts`.
If the credentials are set but Apple rejects them,
generate new ones in Apple School Manager
and enter those.

.. _troubleshooting-host-key:

The upload stops with a missing host key
========================================

The connector verifies the host key of the SFTP server against
:file:`/etc/asm_public_key`.
The package ships that file.
If it's missing or no longer matches the server,
the upload fails with ``Could not find /etc/asm_public_key``
or with an SSH exception.

Reinstall the package to restore the file.
If Apple changed the host key,
report it to Univention,
see :ref:`troubleshooting-support`,
so that a new version of the app can ship the new key.

.. _troubleshooting-ldap-filter:

The upload to an account stops with an invalid LDAP filter
==========================================================

An LDAP filter with a syntax error stops the upload
to the account of that school.
The connector still uploads to the remaining accounts
and exits with a non-zero status at the end.
The log file names the filter and the account.

.. code-block:: text
   :caption: Messages in the log file

   Invalid LDAP-filter for students: '(ucsschoolRole=student'
   Invalid LDAP filter, nothing uploaded to account north.

Correct the filter in the settings file,
or remove the ``ldap_filter`` key of the school
to fall back to the filter in ``defaults``.
See :ref:`configuration-ldap-filter`.

.. _troubleshooting-no-csv:

Classes have fewer teachers than expected
=========================================

Apple School Manager supports at most 15 teachers per class.
The connector exports the first 15
and writes a warning to the log file that names the class.
This is a limitation of Apple School Manager,
not of the connector.

An LDAP filter for teachers can also reduce the number.
The log file records every teacher whom a filter excluded from a class.

.. _troubleshooting-federation-again:

Federation for a domain fails the second time
=============================================

If you disable federation for a domain
and then enable it again,
Apple School Manager shows an error.

While federation is on,
Apple School Manager offers to disconnect the domain
instead of removing it.
Disconnecting removes the domain only from the federation.
The domain itself stays in Apple School Manager.

To enable federation for the domain again,
do the following:

#. In Apple School Manager,
   disconnect the identity provider.

#. Connect it again,
   as described in :ref:`identity-provider-asm-idp`.

#. Enable federation for the domain,
   as described in :ref:`identity-provider-asm-domain`.

.. _troubleshooting-keycloak-settings:

Apple School Manager can't connect to Keycloak
==============================================

If connecting Apple School Manager to Keycloak fails,
or if Keycloak shows no SSF stream for the client afterwards,
run :command:`asm-setup-keycloak` again,
as described in :ref:`identity-provider-keycloak`.
The script restores every setting that differs
from what Apple School Manager needs.

To check the settings yourself,
compare them with the following tables.
They use the names of the Keycloak API.
In the Keycloak admin console,
select the realm ``ucs`` first,
because the console opens in the realm ``master``.

.. list-table:: Settings of the Keycloak app, the realm, and the client scopes
   :header-rows: 1
   :widths: 40 60

   * - Object
     - Setting

   * - Keycloak app
     - App setting ``keycloak/server/feature/ssf``: ``true``

   * - Realm ``ucs``
     - Attribute ``ssf.transmitterEnabled``: ``true``

   * - Client scopes ``ssf.manage`` and ``ssf.read``
     - Attribute ``include.in.token.scope``: ``true``

   * - User ``asm``
     - Client role ``ssf-admin`` of the client ``apple-asm``

.. list-table:: Settings of the client ``apple-asm``
   :header-rows: 1
   :widths: 40 60

   * - Setting
     - Value

   * - ``publicClient``
     - ``false``

   * - ``standardFlowEnabled``
     - ``true``

   * - ``implicitFlowEnabled``, ``directAccessGrantsEnabled``,
       ``serviceAccountsEnabled``
     - ``false``

   * - ``redirectUris``
     - ``https://gsa-ws.apple.com/grandslam/GsService2/acs``

   * - Default client scopes
     - ``ssf.manage``, ``ssf.read``, ``offline_access``

   * - Client role
     - ``ssf-admin``

   * - Attribute ``post.logout.redirect.uris``
     - ``+``

   * - Attribute ``pkce.code.challenge.method``
     - Empty

Apple doesn't appear to support :term:`PKCE` for OIDC federations,
which is why the client turns it off.

The client acts as SSF receiver through the attributes in the following table.

.. list-table:: SSF attributes of the client ``apple-asm``
   :header-rows: 1
   :widths: 40 60

   * - Attribute
     - Value

   * - ``ssf.enabled``
     - ``true``

   * - ``ssf.profile``
     - ``SSE_CAEP``

   * - ``ssf.defaultSubjects``
     - ``NONE``

   * - ``ssf.userSubjectFormat``
     - ``iss_sub``

   * - ``ssf.autoNotifyOnLogin``
     - ``true``

   * - ``ssf.autoVerifyStream``
     - ``true``

   * - ``ssf.verificationDelayMillis``
     - ``1500``

   * - ``ssf.requiredRole``
     - ``apple-asm.ssf-admin``

   * - ``ssf.allowedDeliveryMethods``
     - ``push``

   * - ``ssf.validPushUrls``
     - ``https://federation.apple.com/feeds/school/caep/*``

   * - ``ssf.supportedEvents``
     - ``CaepCredentialChange,CaepSessionRevoked``

   * - ``ssf.allowEmitEvents``
     - ``true``

   * - ``ssf.emitOnlyEvents``
     - ``CaepSessionRevoked``

``ssf.autoVerifyStream`` sends the verification event as soon as Apple
creates the stream.
``ssf.emitOnlyEvents`` lets you control through the Keycloak API when
Keycloak sends a sign-out to Apple.

.. _troubleshooting-support:

Where to get help
=================

* The `Univention Help <https://help.univention.com/>`_ forum
  for questions from the community.

* Your Univention support contract for a supported environment.

When you report a problem,
attach the relevant part of :file:`/var/log/univention/asm.log`.
