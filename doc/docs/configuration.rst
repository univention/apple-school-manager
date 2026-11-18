.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _configuration:

*************
Configuration
*************

The connector reads its configuration from two places.
The settings file :file:`/etc/asm-connections.json` defines the accounts,
schools, exported user accounts, and attribute mappings.
The app settings in the :term:`App Center` define the synchronization schedule
and operational switches.

The following sections describe the settings file,
the app settings,
and the available settings in detail.

The following sections help you configure the connector:

* :ref:`configuration-file` describes the file structure
  and how to configure accounts and schools.

* :ref:`configuration-app-settings` lists the available app settings.

* :ref:`configuration-schedule` explains how to run synchronization daily.

* :ref:`configuration-details` describes optional settings,
  such as anonymization, LDAP filters, and existing locations.

.. caution::

   :term:`Apple School Manager` uses the email address of a user as the *Apple Account*.
   Make sure that every synchronized user has a primary email address.
   *Apple School Manager* can't create an account for a user without one.
   See :ref:`configuration-email`.

.. _configuration-file:

Settings file
=============

This section describes the central configuration file
for the *Apple School Manager Connector*.
The connector configuration file is a JSON text file
with the following sections.
:numref:`configuration-file-listing` shows an example.

.. envvar:: accounts

   The *Apple School Manager* accounts,
   each with its credentials and the settings for the students and teachers
   that the account receives.
   For details, see :ref:`configuration-accounts`.

.. envvar:: schools

   The schools to synchronize, each with the account that receives it
   and the settings for its classes.
   For details, see :ref:`configuration-school-list`.

.. envvar:: defaults

   Settings that apply to every account and every school,
   unless an account or a school entry sets them itself.
   For details, see :ref:`configuration-defaults`.

.. code-block:: json
   :caption: Complete example of :file:`/etc/asm-connections.json`
   :name: configuration-file-listing

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
           "gym123": {
               "account": "north",
               "location_id": "4711",
               "location_name": "Gymnasium Musterstadt"
           },
           "gs456": {
               "account": "south",
               "course_name_pattern": "{name}",
               "student": {"ldap_filter": "(uid=a*)"}
           }
       }
   }

A student or teacher who belongs to several schools appears only once
in an upload to an account.
The upload includes only the schools that refer to that account.
If none of a user's schools refers to an account,
the connector skips that user for the account.
Settings for students and teachers apply per account.
Settings for classes and LDAP filters apply per school.

For every setting,
the connector uses the value from the :envvar:`accounts` or :envvar:`schools` sections,
then the value from the :envvar:`defaults` section,
and then the built-in default.

The connector app installation creates the file
with read permission for the ``root`` user only.
The connector reads the file at the start of each run,
so a change takes effect with the next synchronization.
It validates the complete file before it uploads anything.

.. _configuration-file-behavior-on-problems:

Upload behavior when problems occur
-----------------------------------

The following problems stop the run with an error message
that names the file and the entry:

* A missing file, or a file without an account or a school.

* A missing or unknown key, or a value of the wrong type.

* A school that refers to an account that the file doesn't define.

* A missing or empty password file.

* A username that appears for more than one account.

* A school that doesn't exist, if the file has the entry ``*``.

  A misspelled school would otherwise send its users
  to the account of that entry.

* No account that receives an existing school.

* A :envvar:`location_id` or :envvar:`location_name`
  in :envvar:`defaults` or in the entry ``*``.

* A :envvar:`location_id` that is empty or contains spaces,
  or a :envvar:`location_name` that is empty or contains only spaces.
  To use the default value, omit the key.

* Several schools of one account with the same :envvar:`location_id`
  and different values for :envvar:`location_name`.

* A :envvar:`location_id` that is the abbreviation of another school
  of the same account without :envvar:`location_id`,
  see :ref:`configuration-locations-shared`.

For the following problems,
the connector logs a warning and uploads to the remaining accounts:

* An account that no school refers to.
  The account receives no upload.

* A school that doesn't exist, if the file has no entry ``*``.
  An account without any existing school receives no upload.

If an upload to one account fails,
the connector uploads to the remaining accounts.
It exits with a non-zero status.

.. _configuration-accounts:

Apple School Manager accounts
-----------------------------

The :envvar:`accounts` section assigns a name of your choice
to each :term:`Apple School Manager` account.
The name may contain only letters, digits, ``.``, ``_``, and ``-``.
Usually, you configure one account.
If the schools on your |UAS| system belong to different institutions,
each with its own *Apple School Manager* account,
add one entry for each account.
The connector then uploads a separate archive to each account.
Each archive contains only the schools that refer to that account.

To add an account, edit :file:`/etc/asm-connections.json` as ``root``:

#. Store the account SFTP password in a separate file
   that only ``root`` can read.

   To retrieve the password,
   follow :ref:`installation-credentials`.

   Each account has separate SFTP credentials and needs a separate password file.
   Follow :ref:`installation-configure-credentials` for each account.
   Set the ``password_file`` key to that account's password-file path,
   for example :file:`/etc/asm-north.secret`.

#. Add the account to the :envvar:`accounts` section of the settings file.

#. Assign at least one school to the account,
   as described in :ref:`configuration-school-list`.

An account entry can contain the keys in :numref:`configuration-accounts-table`.
All keys except :envvar:`username` and :envvar:`password_file` are optional.
You can also set optional keys in the :envvar:`defaults` section.

.. envvar:: username

   The SFTP username of the *Apple Account*.

   :Required: Yes

.. envvar:: password_file

   The path to the file that contains the SFTP password of the *Apple Account*.

   :Required: Yes

.. _configuration-accounts-table:

.. list-table:: Keys of an account entry
   :header-rows: 1
   :widths: 5 2 5

   * - Key
     - Default
     - Description

   * - :envvar:`username`
     - Required
     - See :envvar:`username`.

   * - :envvar:`password_file`
     - Required
     - See :envvar:`password_file`.

   * - :envvar:`email_prepend_domain`
     -
     - See :ref:`configuration-email`.

   * - :envvar:`student.anonymize`, :envvar:`staff.anonymize`
     -
     - See :ref:`configuration-anonymization`.

   * - :envvar:`student.anonymize_values`, :envvar:`staff.anonymize_values`
     -
     - See :ref:`configuration-anonymization`.

   * - :envvar:`student.person_id_attribute`, :envvar:`staff.person_id_attribute`
     -
     - See :ref:`configuration-person-id`.

   * - :envvar:`student.password_policy`
     -
     - See :ref:`configuration-password-policy`.

   * - :envvar:`student.grade_level_attribute`
     -
     - See :ref:`configuration-grade-level`.

.. _configuration-school-list:

Schools
-------

The :envvar:`schools` section lists the schools
to synchronize by their abbreviation
and assigns each of them to an account.
The connector only synchronizes schools that the section lists.

To look up the abbreviations,
open :menuselection:`School administration --> Schools` in the :term:`Management UI`.
The abbreviation is the name of the school object, for example ``gym123``.

The entry ``*`` stands for every school that the section doesn't list by name.
With a single account,
it synchronizes all schools to that account.

If the section lists a school that doesn't exist,
the connector stops before it uploads anything.
Otherwise, a misspelled school would go to the account of the entry ``*``
instead of the account you meant.

The example in :numref:`configuration-school-list-example-listing`
assigns every school to the ``north`` account.
It configures a separate LDAP filter for the staff of ``gym123``.

.. code-block:: json
   :caption: Every school to one account, one school with its own LDAP filter
   :name: configuration-school-list-example-listing

   "schools": {
       "*": {"account": "north"},
       "gym123": {
           "account": "north",
           "staff": {"ldap_filter": "(uid=t*)"}
       }
   }

A school entry can contain the keys in :numref:`configuration-school-list-table`.
All keys except :envvar:`account` are optional.
You can also set optional keys in :envvar:`defaults`.

.. envvar:: account

   The name of the account in the :envvar:`accounts` section
   that receives the school

   :Required: Yes

.. _configuration-school-list-table:

.. list-table:: Keys of a school entry
   :header-rows: 1
   :widths: 5 2 5

   * - Key
     - Default
     - Description

   * - :envvar:`account`
     - Required
     - See :envvar:`account`.

   * - :envvar:`course_name_pattern`
     - ``{ou}-{name}``
     - See :ref:`configuration-course-names`.

   * - :envvar:`class_number_empty`
     - ``true``
     - See :ref:`configuration-course-names`.

   * - :envvar:`student.ldap_filter`, :envvar:`staff.ldap_filter`
     - Empty
     - See :ref:`configuration-ldap-filter`.

   * - :envvar:`location_id`, :envvar:`location_name`
     - The school abbreviation and the display name of the school
     - See :ref:`configuration-locations`.

.. _configuration-defaults:

Defaults
--------

The :envvar:`defaults` section can contain every optional key
of an account entry and a school entry,
except :envvar:`location_id` and :envvar:`location_name`.
A value in :envvar:`defaults` applies to every account or school
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

.. versionadded:: 6.0.0

Up to *Apple School Manager Connector* version 5.1.1,
app settings and UCR variables held the configuration.

The update to version 6.0.0 moves their values to the settings file
and removes the UCR variables.
You don't need to do anything.
The password stays in :file:`/etc/asm.secret`.
The settings file refers to :file:`/etc/asm.secret`.
The account gets the name ``default``.

:numref:`configuration-accounts-migration-mapping-table` maps the former app
settings and UCR variables to their corresponding keys in the settings file.

.. _configuration-accounts-migration-mapping-table:

.. list-table:: Former app settings and UCR variables
   :header-rows: 1
   :widths: 50 50

   * - Former setting
     - Key in the settings file

   * - ``asm/username``
     - :envvar:`accounts.default.username <username>`

   * - ``asm/password``
     - :envvar:`accounts.default.password_file <password_file>`

   * - ``asm/school_whitelist``
     - One entry per school in :envvar:`schools`,
       or the entry ``*`` if the list was empty

   * - ``asm/attributes/user/email/prepend_domain``
     - :envvar:`defaults.email_prepend_domain <email_prepend_domain>`

   * - :samp:`asm/attributes/{ROLE}/anonymize`
     - :envvar:`defaults.ROLE.anonymize <student.anonymize>`

   * - :samp:`asm/attributes/{ROLE}/anonymize/{ATTRIBUTE}`
     - :envvar:`defaults.ROLE.anonymize_values.ATTRIBUTE <student.anonymize_values>`

   * - :samp:`asm/attributes/{ROLE}/person_id/mapping`
     - :envvar:`defaults.ROLE.person_id_attribute <student.person_id_attribute>`,
       without the leading ``%``

   * - ``asm/attributes/student/password_policy``
     - :envvar:`defaults.student.password_policy <student.password_policy>`,
       ``null`` for the former ``-``

   * - ``asm/attributes/student/grade_level``
     - :envvar:`defaults.student.grade_level_attribute <student.grade_level_attribute>`

   * - ``asm/attributes/course-name-pattern``
     - :envvar:`defaults.course_name_pattern <course_name_pattern>`

   * - ``asm/attributes/classes/class_number_empty``
     - :envvar:`defaults.class_number_empty <class_number_empty>`

   * - ``asm/ldap_filter/students``, ``asm/ldap_filter/staff``
     - :envvar:`defaults.student.ldap_filter <student.ldap_filter>`, :envvar:`defaults.staff.ldap_filter <staff.ldap_filter>`

   * - :samp:`asm/ldap_filter/students/{SCHOOL}`,
       :samp:`asm/ldap_filter/staff/{SCHOOL}`
     - :envvar:`schools.SCHOOL.student.ldap_filter <student.ldap_filter>`,
       :envvar:`schools.SCHOOL.staff.ldap_filter <staff.ldap_filter>`

Replace the placeholders as follows:

* Replace :samp:`{ROLE}` with ``staff`` or ``student``.

* Replace :samp:`{ATTRIBUTE}` with an attribute from :ref:`configuration-anonymization`.

* Replace :samp:`{SCHOOL}` with the school abbreviation.

The update drops an LDAP filter for a school
that wasn't on the former school list,
because the connector didn't synchronize that school.
It also leaves out schools that don't exist anymore,
both from the former school list and from the LDAP filters,
and prints a note for each of them.

Without ``asm/username``,
the update has no account to assign schools to.
It keeps ``asm/school_whitelist``,
the :samp:`asm/ldap_filter/students/{SCHOOL}`,
:samp:`asm/ldap_filter/staff/{SCHOOL}` UCR variables,
and prints a note for each of them.
Move their values to the settings file
when you add the account.

If the :file:`/etc/asm-connections.json` file already exists,
the update leaves it and the UCR variables unchanged.

.. _configuration-app-settings:

App settings
============

To open the app settings,
select the app in the App Center and click :guilabel:`App settings`.
The app settings apply to every account alike.

The following app settings are available for the *Apple School Manager Connector* app.

.. envvar:: asm/sync_daily

     Run the synchronization once a day.
     See :ref:`configuration-schedule`.

     :Default: ``False``

.. envvar:: asm/sync_daily/hour

     The hour of the day at which the daily synchronization runs.
     Valid values are ``0`` to ``23``.

     :Default: Unset

.. envvar:: asm/run_on_appsetting_save

     Run the synchronization immediately after you save the app settings.

     :Default: ``False``

.. envvar:: asm/store_zip

     Keep the uploaded ZIP archive in :file:`/var/lib/asm/`
     instead of deleting it after the upload.

     :Default: ``False``

.. envvar:: asm/last_upload

     Read-only status field.
     Shows when the connector last uploaded an archive to any account.

     :Default: Unset

.. envvar:: asm/last_upload/ACCOUNT

     Shows when the connector last uploaded an archive to the account :samp:`{ACCOUNT}`.
     Not part of the app settings.

     :Default: Unset

.. _configuration-schedule:

Schedule the synchronization
============================

The connector doesn't run on its own.
Either you run it manually,
as described in :ref:`synchronization-run`,
or you let a cron job run it once a day.

To enable the daily run:

#. In the :term:`Management UI`, navigate to the app
   through :menuselection:`Software --> App Center --> Apple School Manager Connector`.

#. Open the app settings.

#. To schedule the synchronization,
   activate the :guilabel:`asm/sync_daily` checkbox.

#. To configure the run hour,
   select an hour from ``0`` to ``23`` in the :guilabel:`asm/sync_daily/hour` drop-down.

#. Click :guilabel:`Apply changes`.

The connector writes the cron job to the :file:`/etc/cron.d/asm-upload` file.
The job runs at minute 0 of the selected hour.
If you enable the daily run without a valid hour,
the connector writes a comment to the cron file instead of a job,
and no synchronization runs.

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

:term:`Apple School Manager` uses the email address of a user as the *Apple Account*.
The connector exports the primary email address of each user in |UAS|.
*Apple School Manager* doesn't import users without an email address,
because it can't create an *Apple Account* for them.

.. envvar:: email_prepend_domain

   Per account.
   Inserts the value as a subdomain in front of the domain of every email address.
   With the value ``apple``, the connector exports the address
   ``jane@example.com`` as ``jane@apple.example.com``.

   :Default: empty.

.. _configuration-anonymization:

Anonymization
-------------

You can anonymize users
when you don't want to transfer their names
and email addresses.
Anonymization replaces each listed attribute value
with its configured replacement value:

* ``first_name``
* ``middle_name``
* ``last_name``
* ``email_address``
* ``sis_username``

.. caution::

   An anonymized user has no email address,
   unless you configure a replacement value for it.
   Without an email address,
   *Apple School Manager* can't create an *Apple Account* for the user.

   Anonymization and the :ref:`identity-provider` setup exclude each other.
   If you use Keycloak as an identity provider for *Apple School Manager*,
   turn anonymization off.

.. envvar:: student.anonymize

   Per account.
   Enables anonymization for students.

   :Default: ``true``.

.. envvar:: staff.anonymize

   Per account.
   Enables anonymization for teachers.

   :Default: ``true``.

.. envvar:: student.anonymize_values

   Per account.
   Replacement values for the anonymized attributes.
   A value that starts with ``%`` names an LDAP attribute,
   and the connector exports the value of that attribute from the user's LDAP
   object.
   A value without a leading ``%`` is exported literally.
   ``null`` leaves the column empty.
   You only need to list the attributes whose default you want to change.

.. envvar:: staff.anonymize_values

   See :envvar:`student.anonymize_values`

:numref:`configuration-anonymization-table` lists the keys in
``anonymize_values``, their default values, and their required status.
:numref:`configuration-anonymization-example-listing` shows an example
of a settings-file entry.

.. _configuration-anonymization-table:

.. list-table:: Replacement values for anonymized attributes
   :header-rows: 1
   :widths: 4 4 4

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
   :name: configuration-anonymization-example-listing

   "student": {
       "anonymize": true,
       "anonymize_values": {"last_name": "Student"}
   }

.. _configuration-person-id:

Identification of users
-----------------------

*Apple School Manager* identifies a user by the ``person_id`` column.
The connector fills it with an LDAP attribute of the user
that doesn't change when you rename the user.

.. envvar:: student.person_id_attribute

   Per account.
   LDAP attribute that identifies a student or a teacher.

   :Default: ``entryUUID``.

.. envvar:: staff.person_id_attribute

   See :envvar:`student.person_id_attribute`.

.. warning::

   Don't change these keys after the connector has synchronized user accounts.
   *Apple School Manager* treats a user with a new ``person_id``
   as a different user
   and loses the association with the existing account.

.. _configuration-password-policy:

Password policy for students
----------------------------

*Apple School Manager* creates the password for a new student itself.
The password policy determines how long that password is.

*Apple School Manager* doesn't support a password policy for teachers.

.. envvar:: student.password_policy

   Per account.
   Length of the password that Apple creates for a new student.
   Valid values are ``4``, ``6``, ``8``, and ``null``.
   ``null`` means that *Apple School Manager* uses the default of the school.

   :Default: ``4``

.. _configuration-grade-level:

Grade level of students
-----------------------

.. envvar:: student.grade_level_attribute

   Per account.
   LDAP attribute that holds the grade level of a student.
   The connector exports its value in the ``grade_level`` column.

   :Default: ``null``, which leaves the column empty.

.. _configuration-course-names:

Names of courses and classes
----------------------------

|UAS| prefixes each class name with the school abbreviation,
for example ``gym123-1a``.
The connector derives the course name from the class name.

.. envvar:: course_name_pattern

   Per school.
   Pattern for the course name.
   The connector replaces ``{ou}`` with the school abbreviation
   and ``{name}`` with the class name without the school prefix.

   :Default: ``{ou}-{name}``

.. envvar:: class_number_empty

   Per school.
   Leaves the ``class_number`` column empty.
   *Apple School Manager* builds the class name from the course name
   and the class number.
   When both values are identical,
   the class name repeats the course name.

   :Default: ``true``

.. _configuration-locations:

Use existing locations in Apple School Manager
----------------------------------------------

.. versionadded:: 6.1.0

The connector assigns each school to a location in *Apple School Manager*.
By default,
it creates one location for each school,
with the school abbreviation as ``location_id``
and the display name of the school as ``location_name``.

If your *Apple School Manager* account already has locations,
for example from another application such as *Jamf*,
you can assign each school to the ID and the name of its existing location.
The connector then uses these values in all files that it uploads:
the locations,
and the ``location_id`` columns of the students, staff, classes, and courses.

.. important::

   You can only use locations that an SFTP upload created,
   for example the upload of another application.
   *Apple School Manager* stores two IDs for each location:
   an internal ID and the ID from the SFTP upload.
   The connector uses the ID from the SFTP upload.
   A location that you created manually in *Apple School Manager*
   only has the internal ID,
   which the *Apple School Manager* user interface doesn't show.

.. envvar:: location_id

   Per school.
   The ID of the location of the school in *Apple School Manager*.
   The ID must not be empty or contain spaces.

   :Default: the school abbreviation

.. envvar:: location_name

   Per school.
   The name of the location of the school in *Apple School Manager*.
   The name must not be empty or contain only spaces.

   The connector uploads the name with every synchronization,
   so it replaces the name of an existing location in *Apple School Manager*.
   To keep the existing name,
   set :envvar:`location_name` to it.

   :Default: the display name of the school,
      or the school abbreviation if the school has no display name

You can set either key alone.
The connector then uses the default for the other one.
You can't set the keys in :envvar:`defaults` or in the entry ``*``,
because every school that they cover would get the same location.

The example in :numref:`configuration-locations-example-listing`
assigns ``gym123`` to the existing location with the ID ``4711``.

.. code-block:: json
   :caption: Assign a school to an existing location
   :name: configuration-locations-example-listing

   "gym123": {
       "account": "north",
       "location_id": "4711",
       "location_name": "Gymnasium Musterstadt"
   }

To assign a school that the entry ``*`` covers,
add an entry with the abbreviation of the school
and the same :envvar:`account`.
The school then no longer uses the keys of the entry ``*``,
only those of its own entry and of :envvar:`defaults`.
Copy the keys of the entry ``*`` that should still apply to the school.

In :numref:`configuration-locations-catch-all-listing`,
the entry ``*`` sends all schools to the account ``south``
and sets a course name pattern.
The entry ``gs456`` assigns the school ``gs456``
to the existing location with the ID ``4712``.
Because ``gs456`` no longer uses the entry ``*``,
the entry repeats :envvar:`account` and :envvar:`course_name_pattern`.

.. code-block:: json
   :caption: Assign a school that the entry ``*`` covers to an existing location
   :name: configuration-locations-catch-all-listing

   "schools": {
       "*": {
           "account": "south",
           "course_name_pattern": "{name}"
       },
       "gs456": {
           "account": "south",
           "course_name_pattern": "{name}",
           "location_id": "4712"
       }
   }

.. tip::

   Test the location mapping with a small test dataset first,
   for example one school with a few users.
   Check in *Apple School Manager*
   that the users, classes, and courses appear in the expected locations
   before you add the other schools.
   If another source already uploads to the account,
   then a small upload deactivates the users of that source that it doesn't contain.
   For more information, see :ref:`configuration-locations-existing-users`.

.. _configuration-locations-shared:

Several schools in one location
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To upload several schools to one location,
set the same :envvar:`location_id` for each of them.
The connector writes the location once,
and the users, classes, and courses of all these schools refer to it.
A user who belongs to several of these schools gets the location only once.
The connector logs which schools share the location.

The name of the shared location is the :envvar:`location_name`
that one or more of the schools set.
If the schools set different names,
the connector stops with an error.
If none of the schools sets a name,
the connector uses the default name
of the school whose abbreviation comes first in alphabetical order.
If you add a school to a shared location later,
the default name can change.
Set :envvar:`location_name` for one of the schools to keep the name stable.

Classes and courses keep the school abbreviation in their ID,
so classes with the same name from different schools stay separate.

The comparison only applies within one account.
Schools of different accounts can use the same :envvar:`location_id`
without sharing a location.

If a :envvar:`location_id` equals the abbreviation of another school
of the same account that has no :envvar:`location_id`,
the connector stops with an error,
because the two schools would share a location by accident.
To share the location on purpose,
set the :envvar:`location_id` for the other school as well.

.. _configuration-locations-change:

Change the location of a school
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning::

   The connector doesn't migrate anything
   if you change the :envvar:`location_id` of a school
   after the connector uploaded the school.

The next upload refers to the new ID only.
*Apple School Manager* treats it as a different location
and assigns the users, classes, and courses of the school to it.
The previous location remains in *Apple School Manager*
until you remove it there.

.. _configuration-locations-existing-users:

Existing users and classes
~~~~~~~~~~~~~~~~~~~~~~~~~~

If another SFTP upload source already created users and classes
in *Apple School Manager*,
the connector can use the existing users,
but not the existing classes.
No setting maps a |UAS| class to an existing class,
so the connector creates its own classes next to the existing ones,
and the classes appear twice in *Apple School Manager*.
For more information, see :ref:`configuration-locations-existing-classes`.

.. important::

   Prepare the configuration before the first upload of the connector.
   User accounts that the first upload creates by mistake
   remain in *Apple School Manager*.

   The first upload deactivates every user of the other source
   that the connector doesn't send.
   Examples are staff without a teacher role
   and the users of schools that the settings file doesn't list.
   *Apple School Manager* deletes these users after 30 days.
   For more information, see :ref:`synchronization-lifecycle`.

Users
"""""

*Apple School Manager* identifies a user by the ``person_id`` column.
For more information, see :ref:`configuration-person-id`.
If the connector sends the ``person_id`` of an existing user,
then *Apple School Manager* updates that user.
Otherwise, *Apple School Manager* creates a new user,
and the person appears twice.

To use the existing users,
proceed as follows:

#. Store the ID that the other source uploaded as ``person_id``
   in an LDAP attribute of each user,
   for example ``ucsschoolRecordUID``
   if your |UAS| import uses the same IDs as the other source.

#. Set :envvar:`student.person_id_attribute`
   and :envvar:`staff.person_id_attribute` to that attribute
   in the entry of the account that receives the schools.
   Set the keys in :envvar:`defaults` only
   if the connector hasn't synchronized any account yet.
   Otherwise, the ``person_id`` of the users in the synchronized accounts changes,
   and *Apple School Manager* creates these users a second time.

   The keys apply to every school of the account,
   so every user that the connector uploads to the account
   needs a value in the attribute.
   If one user has no value,
   then the connector uploads nothing to the account
   and logs an error with the DN of the user.
   The connector stops at the first user without a value,
   so each run reports only one user.
   To list all students and teachers of a school without a value,
   run the command in :numref:`configuration-locations-missing-person-id-listing`
   for each school of the account.

   .. code-block:: console
      :caption: List the students and teachers of ``gym123`` without ``ucsschoolRecordUID``
      :name: configuration-locations-missing-person-id-listing

      $ univention-ldapsearch -LLL \
        '(&(|(ucsschoolRole=student:school:gym123)(ucsschoolRole=teacher:school:gym123))(!(ucsschoolRecordUID=*)))' uid

#. Assign the schools to the existing locations.
   For more information, see :ref:`configuration-locations`.

*Apple School Manager* updates the existing users
with the values that the connector sends.
With anonymization enabled,
which is the default,
the first name becomes the username,
the last name becomes ``-``,
and the email address stays empty.
The connector then sends the existing users without an email address.
To keep the email addresses,
turn anonymization off
or configure a replacement value for ``email_address``.
For more information, see :ref:`configuration-anonymization`.

The example in :numref:`configuration-locations-existing-users-listing`
identifies the users of the account ``north`` by ``ucsschoolRecordUID``
and assigns ``gym123`` to the existing location with the ID ``4711``.

.. code-block:: json
   :caption: Use existing users and an existing location
   :name: configuration-locations-existing-users-listing

   "accounts": {
       "north": {
           "username": "sftp-user-north",
           "password_file": "/etc/asm-north.secret",
           "student": {"person_id_attribute": "ucsschoolRecordUID"},
           "staff": {"person_id_attribute": "ucsschoolRecordUID"}
       }
   },
   "schools": {
       "gym123": {
           "account": "north",
           "location_id": "4711",
           "location_name": "Gymnasium Musterstadt"
       }
   }

.. _configuration-locations-existing-classes:

Classes
"""""""

The connector uses the |UAS| class name as the ID of the class and the course,
for example ``gym123-1a``.
You can't assign a class to the ID of an existing class.
The connector creates new classes,
and the existing classes remain in *Apple School Manager*:

* The students leave the existing classes with the first upload,
  because every upload replaces the class memberships of the students.

* The teachers remain in the existing classes,
  because the connector doesn't send these classes.
  Teachers therefore see the existing and the new classes.

* You can't delete classes from an SFTP upload in *Apple School Manager*,
  and you can't remove their teachers there.

To remove the teachers from the existing classes,
upload the existing classes once with empty teacher columns.
The other source or the connector can do this upload.

If the other source can still upload,
remove the teachers from the classes in the other source.
Then let the other source upload one last time
before the first upload of the connector.

Otherwise, proceed as follows:

#. Enable :envvar:`asm/store_zip` and run the synchronization.
   This run is the first upload of the connector.
   It creates the new classes,
   and the connector keeps the uploaded archive in :file:`/var/lib/asm/`.
   The connector can't create the archive without uploading it.
   With several accounts,
   the connector keeps one archive for each account.
   The :file:`locations.csv` file in each archive
   lists the locations of the account.

#. Unpack the archive.
   For each existing class,
   add a row to :file:`classes.csv`
   with the ``class_id``, ``course_id``, and ``location_id`` of the class
   and empty ``instructor_id`` columns.
   For each course of these classes,
   copy its row from the :file:`courses.csv` file of the other source
   to the :file:`courses.csv` file of the archive.
   Take the IDs from the files of the other source.

#. Pack the files into a ZIP archive named :file:`archive.zip`
   and upload it with an SFTP client
   to the SFTP account of *Apple School Manager*.
   *Apple School Manager* deactivates every user that an upload doesn't contain,
   so the archive must contain the files of the connector
   in addition to the existing classes.

#. Deactivate :envvar:`asm/store_zip`
   and delete the archives in :file:`/var/lib/asm/`,
   because they contain personal data.

The next uploads of the connector don't contain the existing classes.
*Apple School Manager* keeps them without teachers.

To remove the school abbreviation from the names of the new classes,
set :envvar:`course_name_pattern` to ``{name}``.
For more information, see :ref:`configuration-course-names`.

.. _configuration-ldap-filter:

Select users with an LDAP filter
--------------------------------

If the school list from :ref:`configuration-school-list` isn't specific enough,
you can select the users with an LDAP filter.
The connector applies the filter in addition to the school list.

.. envvar:: student.ldap_filter

   Per school.
   LDAP filter for the students or the teachers of the school.
   A filter in :envvar:`defaults` applies to every school
   that doesn't set its own.

   :Default: empty, which selects every user.

.. envvar:: staff.ldap_filter

   See :envvar:`student.ldap_filter`

The example in :numref:`configuration-ldap-filter-primary-address-example-listing`
synchronizes only students in ``gym123``
who have a primary email address.

.. code-block:: json
   :caption: Synchronize only the students of ``gym123`` with a primary email address
   :name: configuration-ldap-filter-primary-address-example-listing

   "gym123": {
       "account": "north",
       "student": {"ldap_filter": "(mailPrimaryAddress=*)"}
   }

The connector first selects the students or teachers of a school.
It then applies the LDAP filter to that selection.
The filter only needs to describe the user attributes that you want to select.

To verify which users a filter selects before you set it,
combine it with the role of the users and run it with
:command:`univention-ldapsearch`,
as shown in :numref:`configuration-ldap-filter-verify-filter-listing`.

.. code-block:: console
   :caption: List the students of ``gym123`` who match the filter
   :name: configuration-ldap-filter-verify-filter-listing

   $ univention-ldapsearch -LLL \
     '(&(ucsschoolRole=student:school:gym123)(mailPrimaryAddress=*))' uid

.. caution::

   An invalid LDAP filter stops the upload to the account of that school.
   The connector uploads nothing to that account in that case,
   so its data in *Apple School Manager* stays as it was after the last
   successful run.
   The other accounts still receive their upload.
