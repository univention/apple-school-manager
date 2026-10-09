.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration:

*************
Configuration
*************

The connector reads its configuration from two places.
The settings file :file:`/etc/asm-connections.json` holds the Apple School
Manager accounts,
the schools that the connector synchronizes to each of them,
and every setting that controls which users the connector exports
and how it maps their attributes.
The app settings in the :term:`App Center` hold the synchronization schedule
and a few switches for everyday operation.

.. caution::

   Apple School Manager uses the email address of a user as the Apple Account.
   Make sure that every synchronized user has a primary email address.
   Apple School Manager can't create an account for a user without one.
   See :ref:`configuration-email`.

.. _configuration-file:

Settings file
=============

The settings file :file:`/etc/asm-connections.json` has three sections:

``accounts``
   The Apple School Manager accounts, each with its credentials and the
   settings for the students and teachers that the account receives.
   See :ref:`configuration-accounts`.

``schools``
   The schools to synchronize, each with the account that receives it
   and the settings for its classes.
   See :ref:`configuration-school-list`.

``defaults``
   Settings that apply to every account and every school,
   unless an account or a school entry sets them itself.
   See :ref:`configuration-defaults`.

.. code-block:: json
   :caption: Two Apple School Manager accounts in :file:`/etc/asm-connections.json`

   {
       "accounts": {
           "north": {
               "username": "sftp-user-north",
               "password_file": "/etc/asm-north.secret"
           },
           "south": {
               "username": "sftp-user-south",
               "password_file": "/etc/asm-south.secret",
               "student": {"anonymize": false}
           }
       },
       "defaults": {
           "student": {"password_policy": 6}
       },
       "schools": {
           "gym123": {"account": "north"},
           "gs456": {
               "account": "south",
               "course_name_pattern": "{name}",
               "student": {"ldap_filter": "(uid=a*)"}
           }
       }
   }

A student or teacher who belongs to several schools of the same account
appears only once in the upload to that account.
The settings for students and teachers therefore apply per account,
and the settings for classes and the LDAP filters apply per school.

For every setting,
the connector uses the value from the account or school entry,
then the value from ``defaults``,
and then the built-in default.

The installation creates the file
with read permission for the ``root`` user only.
Edit it with a text editor.
The connector reads the file at the start of each run,
so a change takes effect with the next synchronization.
It checks the complete file before it uploads anything.
The following problems stop the run with an error message
that names the file and the entry:

* A missing file, or a file without an account or a school.
* A missing or unknown key, or a value of the wrong type.
* A school that refers to an account that the file doesn't define.
* A missing or empty password file.
* A user name that appears for more than one account.
* A school that doesn't exist, if the file has the entry ``*``.
  A misspelled school would otherwise send its users
  to the account of that entry.
* No account that receives an existing school.

The following problems only write a warning to the log file.
The connector uploads to the remaining accounts:

* An account that no school refers to.
  The account receives no upload.
* A school that doesn't exist, if the file has no entry ``*``.
  An account without any existing school receives no upload.

If the upload to one account fails,
the connector still uploads to the remaining accounts
and exits with a non-zero status at the end.

.. _configuration-accounts:

Apple School Manager accounts
-----------------------------

The ``accounts`` section maps a name of your choice to each account.
The name may only contain letters, digits, ``.``, ``_``, and ``-``.
Usually there is a single account.
If the schools on your |UAS| system belong to different institutions,
each with its own Apple School Manager account,
add one entry per account.
The connector then uploads a separate archive to every account,
each restricted to the schools that refer to that account.

To add an account:

#. Store the SFTP password of the account in a file of its own
   that only ``root`` can read.
   :ref:`installation-credentials` describes where to find the password.
   Every account has its own SFTP credentials,
   so every account needs its own password file.
   The examples name the file after the account,
   such as :file:`/etc/asm-north.secret`.
   The account from :ref:`installation-configure-credentials`
   can keep :file:`/etc/asm.secret`.

   .. code-block:: console
      :caption: Store the password of an account

      $ install -m 600 /dev/null /etc/asm-north.secret
      $ editor /etc/asm-north.secret

#. Add the account to the ``accounts`` section of the settings file.

#. Assign at least one school to the account,
   as described in :ref:`configuration-school-list`.

An account entry takes the following keys.
All keys except ``username`` and ``password_file`` are optional
and can also go to ``defaults``.

.. list-table:: Keys of an account entry
   :header-rows: 1
   :widths: 35 20 45

   * - Key
     - Default
     - Description

   * - ``username``
     - Required
     - The SFTP user name of the account.

   * - ``password_file``
     - Required
     - Path to the file that holds the SFTP password of the account.

   * - ``email_prepend_domain``
     - Empty
     - See :ref:`configuration-email`.

   * - ``student.anonymize``, ``staff.anonymize``
     - ``true``
     - See :ref:`configuration-anonymization`.

   * - ``student.anonymize_values``, ``staff.anonymize_values``
     - See :ref:`configuration-anonymization`
     - See :ref:`configuration-anonymization`.

   * - ``student.person_id_attribute``, ``staff.person_id_attribute``
     - ``entryUUID``
     - See :ref:`configuration-person-id`.

   * - ``student.password_policy``
     - ``4``
     - See :ref:`configuration-password-policy`.

   * - ``student.grade_level_attribute``
     - ``null``
     - See :ref:`configuration-grade-level`.

.. _configuration-school-list:

Schools
-------

The ``schools`` section lists the schools to synchronize
by their abbreviation
and assigns each of them to an account.
The connector only synchronizes schools that the section lists.

To look up the abbreviations,
open :menuselection:`School administration --> Schools` in :term:`UMC`.
The abbreviation is the name of the school object, for example ``gym123``.

The entry ``*`` stands for every school that the section doesn't list by name.
With a single account,
it synchronizes all schools to that account.

If the section lists a school that doesn't exist,
the connector stops before it uploads anything.
Otherwise a misspelled school would go to the account of the entry ``*``
instead of the account you meant.

.. code-block:: json
   :caption: Every school to one account, one school with its own LDAP filter

   "schools": {
       "*": {"account": "north"},
       "gym123": {
           "account": "north",
           "staff": {"ldap_filter": "(uid=t*)"}
       }
   }

A student or teacher who belongs to several schools
appears in the upload to an account
only with the schools that belong to that account.
If none of their schools belongs to the account,
the connector skips them for that account.

A school entry takes the following keys.
All keys except ``account`` are optional
and can also go to ``defaults``.

.. list-table:: Keys of a school entry
   :header-rows: 1
   :widths: 35 20 45

   * - Key
     - Default
     - Description

   * - ``account``
     - Required
     - Name of the account in the ``accounts`` section
       that receives the school.

   * - ``course_name_pattern``
     - ``{ou}-{name}``
     - See :ref:`configuration-course-names`.

   * - ``class_number_empty``
     - ``true``
     - See :ref:`configuration-course-names`.

   * - ``student.ldap_filter``, ``staff.ldap_filter``
     - Empty
     - See :ref:`configuration-ldap-filter`.

.. _configuration-defaults:

Defaults
--------

The ``defaults`` section takes every optional key of an account entry
and of a school entry.
A value in ``defaults`` applies to every account or every school
that doesn't set the key itself.

.. code-block:: json
   :caption: Anonymize nobody, except the students of the account ``north``

   "defaults": {
       "student": {"anonymize": false},
       "staff": {"anonymize": false}
   },
   "accounts": {
       "north": {
           "username": "sftp-user-north",
           "password_file": "/etc/asm-north.secret",
           "student": {"anonymize": true}
       }
   }

.. _configuration-accounts-migration:

Update from an earlier version
------------------------------

Up to version 5.1.1,
app settings and UCR variables held the configuration.
The update to version 5.2.0 moves their values to the settings file
and removes the UCR variables.
You don't need to do anything.
The password stays in :file:`/etc/asm.secret`,
and the settings file refers to it.
The account gets the name ``default``.

.. list-table:: Former app settings and UCR variables
   :header-rows: 1
   :widths: 50 50

   * - Former setting
     - Key in the settings file

   * - ``asm/username``
     - ``accounts.default.username``

   * - ``asm/password``
     - ``accounts.default.password_file``

   * - ``asm/school_whitelist``
     - One entry per school in ``schools``,
       or the entry ``*`` if the list was empty

   * - ``asm/attributes/user/email/prepend_domain``
     - ``defaults.email_prepend_domain``

   * - ``asm/attributes/ROLE/anonymize``
     - ``defaults.ROLE.anonymize``

   * - ``asm/attributes/ROLE/anonymize/ATTRIBUTE``
     - ``defaults.ROLE.anonymize_values.ATTRIBUTE``

   * - ``asm/attributes/ROLE/person_id/mapping``
     - ``defaults.ROLE.person_id_attribute``,
       without the leading ``%``

   * - ``asm/attributes/student/password_policy``
     - ``defaults.student.password_policy``,
       ``null`` for the former ``-``

   * - ``asm/attributes/student/grade_level``
     - ``defaults.student.grade_level_attribute``

   * - ``asm/attributes/course-name-pattern``
     - ``defaults.course_name_pattern``

   * - ``asm/attributes/classes/class_number_empty``
     - ``defaults.class_number_empty``

   * - ``asm/ldap_filter/students``, ``asm/ldap_filter/staff``
     - ``defaults.student.ldap_filter``, ``defaults.staff.ldap_filter``

   * - ``asm/ldap_filter/students/SCHOOL``,
       ``asm/ldap_filter/staff/SCHOOL``
     - ``schools.SCHOOL.student.ldap_filter``,
       ``schools.SCHOOL.staff.ldap_filter``

Replace ``ROLE`` with ``staff`` or ``student``,
``ATTRIBUTE`` with an attribute from :ref:`configuration-anonymization`,
and ``SCHOOL`` with the school abbreviation.

The update drops an LDAP filter for a school
that wasn't on the former school list,
because the connector didn't synchronize that school.

Without ``asm/username``,
the update has no account to assign schools to.
It keeps ``asm/school_whitelist``
and the ``asm/ldap_filter/students/SCHOOL`` and ``asm/ldap_filter/staff/SCHOOL`` UCR variables
and prints a note for each of them.
Move their values to the settings file
when you add the account.

If :file:`/etc/asm-connections.json` already exists,
the update leaves it and the UCR variables unchanged.

.. _configuration-app-settings:

App settings
============

To open the app settings,
select the app in the App Center and click :guilabel:`App settings`.
The app settings apply to every account alike.

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
       Shows when the connector last uploaded an archive to any account.

   * - ``asm/last_upload/ACCOUNT``
     - Unset
     - Shows when the connector last uploaded an archive to the account ``ACCOUNT``.
       Not part of the app settings.

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

.. _configuration-details:

Settings in detail
==================

The following sections describe the optional keys of the settings file.
Keys that start with ``student`` or ``staff``
go into an object of that name,
as in ``"student": {"anonymize": false}``.

.. _configuration-email:

Email addresses
---------------

Apple School Manager uses the email address of a user as the Apple Account.
The connector exports the primary email address of each user in |UAS|.
Users without one are exported without an email address,
and Apple School Manager can't create an Apple Account for them.

``email_prepend_domain``
   Per account.
   Inserts the value as a subdomain in front of the domain of every email
   address.
   With the value ``apple``, the connector exports the address
   ``jane@example.com`` as ``jane@apple.example.com``.
   Default: empty.

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

``student.anonymize``, ``staff.anonymize``
   Per account.
   Enables anonymization for students and teachers.
   Default: ``true``.

``student.anonymize_values``, ``staff.anonymize_values``
   Per account.
   Replacement values for the anonymized attributes.
   A value that starts with ``%`` names an LDAP attribute,
   and the connector exports the value of that attribute from the user's LDAP
   object.
   A value without a leading ``%`` is exported literally.
   ``null`` leaves the column empty.
   You only need to list the attributes whose default you want to change.

.. list-table:: Replacement values for anonymized attributes
   :header-rows: 1
   :widths: 40 30 30

   * - Key in ``anonymize_values``
     - Default
     - Required

   * - ``first_name``
     - ``%uid``
     - Yes

   * - ``middle_name``
     - ``null``
     - No

   * - ``last_name``
     - ``-``
     - Yes

   * - ``email_address``
     - ``null``
     - No

   * - ``sis_username``
     - ``%uid``
     - No

.. code-block:: json
   :caption: Anonymize students with a fixed last name

   "student": {
       "anonymize": true,
       "anonymize_values": {"last_name": "Student"}
   }

.. _configuration-person-id:

Identification of users
-----------------------

Apple School Manager identifies a user by the ``person_id`` column.
The connector fills it with an LDAP attribute of the user
that doesn't change when you rename the user.

``student.person_id_attribute``, ``staff.person_id_attribute``
   Per account.
   LDAP attribute that identifies a student or a teacher.
   Default: ``entryUUID``.

.. caution::

   Don't change these keys on a running installation.
   Apple School Manager treats a user with a new ``person_id``
   as a different user
   and loses the association with the existing account.

.. _configuration-password-policy:

Password policy for students
----------------------------

Apple School Manager creates the password for a new student itself.
The password policy determines how long that password is.

``student.password_policy``
   Per account.
   Length of the password that Apple creates for a new student.
   Valid values are ``4``, ``6``, ``8``, and ``null``.
   ``null`` means that Apple School Manager uses the default of the school.
   Default: ``4``.

Apple School Manager doesn't support a password policy for teachers.

.. _configuration-grade-level:

Grade level of students
-----------------------

``student.grade_level_attribute``
   Per account.
   LDAP attribute that holds the grade level of a student.
   The connector exports its value in the ``grade_level`` column.
   Default: ``null``, which leaves the column empty.

.. _configuration-course-names:

Names of courses and classes
----------------------------

|UAS| prefixes the name of a school class with the school abbreviation,
for example ``gym123-1a``.
The connector derives the course name from that name.

``course_name_pattern``
   Per school.
   Pattern for the course name.
   The connector replaces ``{ou}`` with the school abbreviation
   and ``{name}`` with the class name without the school prefix.
   Default: ``{ou}-{name}``.

``class_number_empty``
   Per school.
   Leaves the ``class_number`` column empty.
   Apple School Manager builds the name of a class from the course name and the
   class number,
   so an identical class number only repeats the course name.
   Default: ``true``.

.. _configuration-ldap-filter:

Select users with an LDAP filter
--------------------------------

If the school list from :ref:`configuration-school-list` isn't fine-grained
enough,
you can select the users with an LDAP filter.
The connector applies the filter in addition to the school list.

``student.ldap_filter``, ``staff.ldap_filter``
   Per school.
   LDAP filter for the students or the teachers of the school.
   A filter in ``defaults`` applies to every school
   that doesn't set its own.
   Default: empty, which selects every user.

.. code-block:: json
   :caption: Synchronize only the students of ``gym123`` with a primary email address

   "gym123": {
       "account": "north",
       "student": {"ldap_filter": "(mailPrimaryAddress=*)"}
   }

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

   An invalid LDAP filter stops the upload to the account of that school.
   The connector uploads nothing to that account in that case,
   so its data in Apple School Manager stays as it was after the last
   successful run.
   The other accounts still receive their upload.
