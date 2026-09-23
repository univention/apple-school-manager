.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration:

*************
Configuration
*************

The connector reads its configuration from three places.
The file :file:`/etc/asm-connections.json` holds the Apple School Manager
accounts and the schools that the connector synchronizes to each of them.
The app settings in the :term:`App Center` hold the synchronization schedule
and a few switches for everyday operation.
The :term:`UCR` holds the settings that control which users the connector
exports and how it maps their attributes.

.. caution::

   Apple School Manager uses the email address of a user as the Apple Account.
   Make sure that every synchronized user has a primary email address.
   Apple School Manager can't create an account for a user without one.
   See :ref:`configuration-email`.

.. _configuration-accounts:

Apple School Manager accounts
=============================

The connector uploads to every Apple School Manager account that is listed in
:file:`/etc/asm-connections.json`.
Usually that is a single account.
If the schools on your UCS\@school system belong to different institutions,
each with its own Apple School Manager account,
list one entry per account.
The connector then uploads a separate archive to every account,
each restricted to the schools that you assign to that account.

To configure the accounts:

#. Store the SFTP password of each account in a file of its own
   that only ``root`` can read.
   :ref:`installation-credentials` describes where to find the password.

   .. code-block:: console
      :caption: Store the password of an account

      $ install -m 600 /dev/null /etc/asm-gym123.secret
      $ editor /etc/asm-gym123.secret

#. Write :file:`/etc/asm-connections.json` with one entry per account.

   .. code-block:: json
      :caption: Two Apple School Manager accounts in :file:`/etc/asm-connections.json`

      [
          {
              "username": "sftp-user-of-account-1",
              "password_file": "/etc/asm-gym123.secret",
              "school_whitelist": ["gym123"]
          },
          {
              "username": "sftp-user-of-account-2",
              "password_file": "/etc/asm-gs456.secret",
              "school_whitelist": ["gs456", "rs789"]
          }
      ]

Each entry takes the following keys:

.. list-table:: Keys of an account entry
   :header-rows: 1
   :widths: 25 15 60

   * - Key
     - Required
     - Description

   * - ``username``
     - Yes
     - The SFTP user name of the account.

   * - ``password_file``
     - Yes
     - Path to the file that holds the SFTP password of the account.

   * - ``school_whitelist``
     - See description
     - List of school abbreviations to synchronize to the account,
       as described in :ref:`configuration-school-list`.
       Required if the file lists more than one account.
       With a single account and no list,
       the connector synchronizes every school.

The connector reads the file at the start of each run,
so a change takes effect with the next synchronization.
It checks the complete file before it uploads anything.
A missing file, a missing or unknown key, a missing password file,
or a user name that appears twice stops the run with an error message.
If the upload to one account fails,
the connector still uploads to the remaining accounts
and exits with a non-zero status at the end.

The app settings and UCR variables apply to every account alike.

.. _configuration-accounts-migration:

Update from an earlier version
------------------------------

Up to version 5.1.1,
the app settings ``asm/username``, ``asm/password``,
and ``asm/school_whitelist`` held the single account.
The update to version 5.2.0 moves them to
:file:`/etc/asm-connections.json`
and removes the UCR variables ``asm/username`` and ``asm/school_whitelist``.
The password stays in :file:`/etc/asm.secret`,
and the new file refers to it.
You don't need to do anything.

If :file:`/etc/asm-connections.json` already exists,
the update leaves it unchanged.

.. _configuration-app-settings:

App settings
============

To open the app settings,
select the app in the App Center and click :guilabel:`App settings`.

.. list-table:: App settings of the Apple School Manager Connector
   :header-rows: 1
   :widths: 30 15 55

   * - Setting
     - Default
     - Description

   * - ``asm/sync_daily``
     - ``False``
     - Run the synchronization once a day.
       See :ref:`configuration-schedule`.

   * - ``asm/sync_daily/hour``
     - Unset
     - The hour of the day at which the daily synchronization runs.
       Valid values are ``0`` to ``23``.

   * - ``asm/run_on_appsetting_save``
     - ``False``
     - Run the synchronization immediately after you save the app settings.

   * - ``asm/store_zip``
     - ``False``
     - Keep the uploaded ZIP archive in :file:`/var/lib/asm/`
       instead of deleting it after the upload.

   * - ``asm/last_upload``
     - Unset
     - Read-only status field.
       Shows when the connector last uploaded an archive.

.. _configuration-schedule:

Schedule the synchronization
============================

The connector doesn't run on its own.
Either you run it manually,
as described in :ref:`synchronization-run`,
or you let a cron job run it once a day.

To enable the daily run:

#. Open the app settings.

#. Select :guilabel:`asm/sync_daily`.

#. Select the hour in :guilabel:`asm/sync_daily/hour`.

#. Click :guilabel:`Apply changes`.

The connector writes the cron job to :file:`/etc/cron.d/asm-upload`.
The job runs at minute 0 of the selected hour.
If you enable the daily run without a valid hour,
the connector writes a comment to the cron file instead of a job,
and no synchronization takes place.

.. _configuration-school-list:

Limit the synchronization to individual schools
===============================================

By default, the connector synchronizes every school that it can see.
To restrict an account to individual schools,
list their abbreviations in the ``school_whitelist`` key of the account in
:file:`/etc/asm-connections.json`.

To look up the abbreviations,
open :menuselection:`School administration --> Schools` in :term:`UMC`.
The abbreviation is the name of the school object, for example ``gym123``.

.. code-block:: json
   :caption: Account restricted to two schools

   {
       "username": "sftp-user",
       "password_file": "/etc/asm.secret",
       "school_whitelist": ["gym123", "gs456"]
   }

A user who belongs to several schools appears in the export only with those
schools that are on the list.
If none of the user's schools is on the list,
the connector skips the user.

.. _configuration-ucr:

Univention Configuration Registry variables
===========================================

The following sections describe the UCR variables of the connector.
You set them in :menuselection:`System --> Univention Configuration Registry`
in UMC,
or on the command line with :command:`ucr set`.
The connector reads them at the start of each run,
so a change takes effect with the next synchronization.

.. _configuration-email:

Email addresses
---------------

Apple School Manager uses the email address of a user as the Apple Account.
The connector exports the primary email address of each user in UCS\@school.
Users without one are exported without an email address,
and Apple School Manager can't create an Apple Account for them.

The connector checks whether the second-level domain of the email address
resolves in the :term:`DNS`.
If it doesn't, the connector writes a warning to the log file
and exports the address unchanged.

.. envvar:: asm/attributes/user/email/prepend_domain

   Inserts the value as a subdomain in front of the domain of every email
   address.
   With the value ``apple``, the connector exports the address
   ``jane@example.com`` as ``jane@apple.example.com``.

   :Default value: Unset
   :Type: string

.. _configuration-anonymization:

Anonymization
-------------

If you don't want to transfer the names and email addresses of your users,
you can anonymize them.
Anonymization replaces the values of the attributes ``first_name``,
``middle_name``, ``last_name``, ``email_address``, and ``sis_username``
with values that you configure.

.. caution::

   An anonymized user has no email address,
   unless you configure a replacement value for it.
   Without an email address,
   Apple School Manager can't create an Apple Account for the user.

   Anonymization and the :ref:`identity-provider` setup exclude each other.
   If you use Keycloak as an identity provider for Apple School Manager,
   turn anonymization off.

.. envvar:: asm/attributes/staff/anonymize

   Enables anonymization for teachers.

   :Default value: ``false``
   :Type: boolean

.. envvar:: asm/attributes/student/anonymize

   Enables anonymization for students.

   :Default value: ``false``
   :Type: boolean

For each anonymized attribute,
a separate variable holds the replacement value.
A value that starts with ``%`` names an LDAP attribute,
and the connector exports the value of that attribute from the user's LDAP
object.
A value without a leading ``%`` is exported literally.

.. list-table:: Replacement values for anonymized attributes
   :header-rows: 1
   :widths: 55 20 25

   * - UCR variable
     - Default
     - Required

   * - ``asm/attributes/ROLE/anonymize/first_name``
     - ``%uid``
     - Yes

   * - ``asm/attributes/ROLE/anonymize/middle_name``
     - Empty
     - No

   * - ``asm/attributes/ROLE/anonymize/last_name``
     - ``No Name``
     - Yes

   * - ``asm/attributes/ROLE/anonymize/email_address``
     - Empty
     - No

   * - ``asm/attributes/ROLE/anonymize/sis_username``
     - ``%uid``
     - No

Replace ``ROLE`` with ``staff`` or ``student``.

.. _configuration-person-id:

Identification of users
-----------------------

Apple School Manager identifies a user by the ``person_id`` column.
The connector fills it with an LDAP attribute of the user
that doesn't change when you rename the user.

.. envvar:: asm/attributes/staff/person_id/mapping

   LDAP attribute that identifies a teacher.

   :Default value: ``%entryUUID``
   :Type: string

.. envvar:: asm/attributes/student/person_id/mapping

   LDAP attribute that identifies a student.

   :Default value: ``%entryUUID``
   :Type: string

.. caution::

   Don't change these variables on a running installation.
   Apple School Manager treats a user with a new ``person_id``
   as a different user
   and loses the association with the existing account.

.. _configuration-password-policy:

Password policy for students
----------------------------

Apple School Manager creates the password for a new student itself.
The password policy determines how long that password is.

.. envvar:: asm/attributes/student/password_policy

   Length of the password that Apple creates for a new student.
   The value ``-`` means that Apple School Manager uses the default of the
   school.

   :Default value: ``4``
   :Possible values: ``4``, ``6``, ``8``, ``-``
   :Type: string

Apple School Manager doesn't support a password policy for teachers.
A value other than the ones listed makes the synchronization stop with an
error.

.. _configuration-grade-level:

Grade level of students
-----------------------

.. envvar:: asm/attributes/student/grade_level

   LDAP attribute that holds the grade level of a student.
   The connector exports its value in the ``grade_level`` column.
   If unset, the column stays empty.

   :Default value: Unset
   :Type: string

.. _configuration-course-names:

Names of courses and classes
----------------------------

UCS\@school prefixes the name of a school class with the school abbreviation,
for example ``gym123-1a``.
The connector derives the course name from that name.

.. envvar:: asm/attributes/course-name-pattern

   Pattern for the course name.
   The connector replaces ``{ou}`` with the school abbreviation
   and ``{name}`` with the class name without the school prefix.

   :Default value: ``{ou}-{name}``
   :Type: string

.. envvar:: asm/attributes/classes/class_number_empty

   Leaves the ``class_number`` column empty.
   Apple School Manager builds the name of a class from the course name and the
   class number,
   so an identical class number only repeats the course name.

   :Default value: ``true``
   :Type: boolean

.. _configuration-ldap-filter:

Select users with an LDAP filter
--------------------------------

If the school list from :ref:`configuration-school-list` isn't fine-grained
enough,
you can select the users with an LDAP filter.
The connector applies the filter in addition to the school list.

.. envvar:: asm/ldap_filter/students

   LDAP filter for the students of every school.

   :Default value: Unset
   :Type: string

.. envvar:: asm/ldap_filter/staff

   LDAP filter for the teachers of every school.

   :Default value: Unset
   :Type: string

A filter for an individual school overrides the global filter.
Append the school abbreviation to the variable name for that,
as in ``asm/ldap_filter/students/SCHOOL``.
Replace ``SCHOOL`` with the school abbreviation, for example ``gym123``.

.. code-block:: console
   :caption: Synchronize only the students of ``gym123`` with a primary email address

   $ ucr set asm/ldap_filter/students/gym123='(mailPrimaryAddress=*)'

The connector combines the filter with its own selection of the students or
teachers of the school,
so the filter only needs to describe the attributes of the users you want.
To check which users a filter selects before you set it,
combine it with the role of the users and run it with
:command:`univention-ldapsearch`:

.. code-block:: console
   :caption: List the students of ``gym123`` who match the filter

   $ univention-ldapsearch -LLL \
     '(&(ucsschoolRole=student:school:gym123)(mailPrimaryAddress=*))' uid

.. caution::

   An invalid LDAP filter stops the synchronization.
   The connector uploads nothing in that case,
   so the data in Apple School Manager stays as it was after the last
   successful run.
