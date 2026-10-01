.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration:

*************
Configuration
*************

The connector reads its configuration from two places.
The app settings in the :term:`App Center` hold the settings that you need for
everyday operation,
such as the credentials and the synchronization schedule.
The :term:`UCR` holds the settings that control which users the connector
exports and how it maps their attributes.

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

   * - ``asm/username``
     - Unset
     - The SFTP user name from Apple School Manager.
       See :ref:`installation-credentials`.

   * - ``asm/password``
     - Unset
     - The SFTP password from Apple School Manager.
       The connector stores it in :file:`/etc/asm.secret`.

   * - ``asm/school_whitelist``
     - Unset
     - Comma-separated list of school abbreviations to synchronize.
       If unset, the connector synchronizes every school.
       See :ref:`configuration-school-list`.

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
To restrict it to individual schools,
list their abbreviations in the ``asm/school_whitelist`` setting,
separated by commas.

To look up the abbreviations,
open :menuselection:`School administration --> Schools` in :term:`UMC`.
The abbreviation is the name of the school object, for example ``gym123``.

.. code-block::
   :caption: Example value for ``asm/school_whitelist``

   gym123,gs456

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

   :Default: Unset

   Inserts the value as a subdomain in front of the domain of every email
   address.
   With the value ``apple``, the connector exports the address
   ``jane@example.com`` as ``jane@apple.example.com``.

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

   :Default: ``false``

   Enables anonymization for teachers.

.. envvar:: asm/attributes/student/anonymize

   :Default: ``false``

   Enables anonymization for students.

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

   * - :samp:`asm/attributes/{role}/anonymize/first_name`
     - ``%uid``
     - Yes

   * - :samp:`asm/attributes/{role}/anonymize/middle_name`
     - Empty
     - No

   * - :samp:`asm/attributes/{role}/anonymize/last_name`
     - ``No Name``
     - Yes

   * - :samp:`asm/attributes/{role}/anonymize/email_address`
     - Empty
     - No

   * - :samp:`asm/attributes/{role}/anonymize/sis_username`
     - ``%uid``
     - No

Replace :samp:`{role}` with ``staff`` or ``student``.

.. _configuration-person-id:

Identification of users
-----------------------

Apple School Manager identifies a user by the ``person_id`` column.
The connector fills it with an LDAP attribute of the user
that doesn't change when you rename the user.

.. envvar:: asm/attributes/staff/person_id/mapping

   :Default: ``%entryUUID``

   LDAP attribute that identifies a teacher.

.. envvar:: asm/attributes/student/person_id/mapping

   :Default: ``%entryUUID``

   LDAP attribute that identifies a student.

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

   :Default: ``4``

   Length of the password that Apple creates for a new student.
   Valid values are ``4``, ``6``, ``8``, and the dash (``-``).
   The dash means that Apple School Manager uses the default of the school.

Apple School Manager doesn't support a password policy for teachers.
A value other than the ones listed makes the synchronization stop with an
error.

.. _configuration-grade-level:

Grade level of students
-----------------------

.. envvar:: asm/attributes/student/grade_level

   :Default: Unset

   LDAP attribute that holds the grade level of a student.
   The connector exports its value in the ``grade_level`` column.
   If unset, the column stays empty.

.. _configuration-course-names:

Names of courses and classes
----------------------------

UCS\@school prefixes the name of a school class with the school abbreviation,
for example ``gym123-1a``.
The connector derives the course name from that name.

.. envvar:: asm/attributes/course-name-pattern

   :Default: ``{ou}-{name}``

   Pattern for the course name.
   The connector replaces ``{ou}`` with the school abbreviation
   and ``{name}`` with the class name without the school prefix.

.. envvar:: asm/attributes/classes/class_number_empty

   :Default: ``true``

   Leaves the ``class_number`` column empty.
   Apple School Manager builds the name of a class from the course name and the
   class number,
   so an identical class number only repeats the course name.

.. _configuration-ldap-filter:

Select users with an LDAP filter
--------------------------------

If the school list from :ref:`configuration-school-list` isn't fine-grained
enough,
you can select the users with an LDAP filter.
The connector applies the filter in addition to the school list.

.. envvar:: asm/ldap_filter/students

   :Default: Unset

   LDAP filter for the students of every school.

.. envvar:: asm/ldap_filter/staff

   :Default: Unset

   LDAP filter for the teachers of every school.

A filter for an individual school overrides the global filter.
Append the school abbreviation to the variable name for that,
as in :samp:`asm/ldap_filter/students/{gym123}`.

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
