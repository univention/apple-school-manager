.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _synchronization:

***************
Synchronization
***************

A synchronization run of the *Apple School Manager Connector*
reads the school data from the LDAP directory,
writes it to CSV files,
packs the files into a ZIP archive,
and uploads the archive to *Apple School Manager*.
This chapter describes the run itself
and the data that it transfers.

.. _synchronization-run:

Run the synchronization
=======================

The following triggers start a synchronization run:

* The cron job from :ref:`configuration-schedule`.

* Saving the app settings,
  if you enabled :envvar:`asm/run_on_appsetting_save`.

* Running the :command:`asm-upload` command,
  as shown in :numref:`synchronization-run-command-listing`.

  The command writes progress messages to the terminal
  and a more detailed log to :file:`/var/log/univention/asm.log`.
  It exits with a non-zero status
  if the credentials are missing
  or if the upload to any account fails.

  .. code-block:: console
     :caption: Start a synchronization run manually
     :name: synchronization-run-command-listing

     $ /usr/sbin/asm-upload

.. _synchronization-run-steps:

What happens during a run
-------------------------

A synchronization has the following steps:

#. The connector reads the settings file :file:`/etc/asm-connections.json`,
   as described in :ref:`configuration-file`.

   For information about the connector's behavior when problem occur,
   see :ref:`configuration-file-behavior-on-problems`.

#. The connector collects information about schools, classes, work groups, teachers,
   and students from the LDAP directory.
   It restricts the data to the account's schools
   and applies the LDAP filters configured in :ref:`configuration-ldap-filter`.

#. The connector writes the CSV files to a temporary directory.
   For more information about the files, see
   :ref:`synchronization-csv-files`.

#. The connector archives the CSV files into
   a file following the pattern
   :file:`/var/lib/asm/asm_{TIMESTAMP}.zip`
   and removes the temporary directory.

   :samp:`TIMESTAMP` is the time the connector created the archive,
   in ISO 8601 format,
   for example ``2026-10-01T03:00:12.345678``.

#. The connector opens an SFTP connection to
   ``upload.appleschoolcontent.com``
   and uploads the archive as :file:`archive.zip`.
   It verifies the host key against the key in the :file:`/etc/asm_public_key` file.

#. The connector sets :envvar:`asm/last_upload`
   and :envvar:`asm/last_upload/ACCOUNT` to the current time
   and deletes the archive,
   unless you enabled :envvar:`asm/store_zip`.

With several accounts,
the connector repeats the steps 2 to 6 for each account.

Every run transfers the complete data set.
The connector doesn't track what changed since the last run.

.. _synchronization-lifecycle:

How Apple School Manager applies the data
-----------------------------------------

*Apple School Manager* compares the uploaded data with its existing accounts
and then does the following:

* It creates a user account when no matching account exists.

* When the user no longer appears in the upload,
  it deactivates the user account immediately
  and deletes it after 30 days.

* If the ``person_id`` column remains unchanged,
  it updates a user account whose attributes have changed.
  For more information, see
  :ref:`configuration-person-id`.

.. _synchronization-csv-files:

The CSV files
=============

The archive contains the CSV files listed in :numref:`synchronization-csv-files-table`.
Apple documents the CSV file format in :cite:p:`apple-sis-csv`.
The connector sorts the rows of each file by school
and then by user or class name.

.. _synchronization-csv-files-table:

.. list-table:: Files in the uploaded archive
   :header-rows: 1
   :widths: 2 9 1

   * - File
     - Content
     - Details

   * - :file:`locations.csv`
     - One row per school.
     - :ref:`synchronization-locations`

   * - :file:`courses.csv`
     - One row per school class and work group.
     - :ref:`synchronization-courses`

   * - :file:`classes.csv`
     - One row per school class and work group,
       with the teachers of that class.
     - :ref:`synchronization-classes`

   * - :file:`staff.csv`
     - One row per teacher.
     - :ref:`synchronization-staff`

   * - :file:`students.csv`
     - One row per student.
     - :ref:`synchronization-students`

   * - :file:`rosters.csv`
     - One row per membership of a student in a school class or work group.
     - :ref:`synchronization-rosters`

.. _synchronization-locations:

Locations
---------

The :file:`locations.csv` file has the columns listed in :numref:`synchronization-locations-table`.

.. _synchronization-locations-table:

.. list-table:: Columns of :file:`locations.csv`
   :header-rows: 1
   :widths: 3 9

   * - Column
     - Source in |UAS|

   * - ``location_id``
     - Name of the school, for example ``gym123``.

   * - ``location_name``
     - Display name of the school.
       The connector uses the school name if the school has no display name.

.. _synchronization-courses:

Courses
-------

*Apple School Manager* requires a course for every class.
|UAS| only has the school class or work group.
Therefore, the connector exports each of them twice:

* As a course in :file:`courses.csv`.
* As a class of that course in :file:`classes.csv`.

Both rows use the name of the group as their ID,
so each course has exactly one class.

The :file:`courses.csv` file has the columns listed in :numref:`synchronization-courses-table`.

.. _synchronization-courses-table:

.. list-table:: Columns of :file:`courses.csv`
   :header-rows: 1
   :widths: 3 9

   * - Column
     - Source in |UAS|

   * - ``course_id``
     - Name of the school class or work group,
       including the school prefix, for example ``gym123-1a``.

   * - ``course_number``
     - Uses the same value as ``course_id``.

   * - ``course_name``
     - Built from ``course_name_pattern``.
       See :ref:`configuration-course-names`.

   * - ``location_id``
     - Name of the school.

.. _synchronization-classes:

Classes
-------

The :file:`classes.csv` file has the columns listed in :numref:`synchronization-classes-table`.

.. _synchronization-classes-table:

.. list-table:: Columns of :file:`classes.csv`
   :header-rows: 1
   :widths: 3 9

   * - Column
     - Source in |UAS|

   * - ``class_id``
     - Name of the school class or work group.

   * - ``class_number``
     - The field is empty by default.
       See :envvar:`class_number_empty`.

   * - ``course_id``
     - Name of the school class or work group.

   * - ``instructor_id``, ``instructor_id_2``, ``instructor_id_3``
     - The ``person_id`` of the first three teachers of the class.

   * - ``instructor_id_4`` to ``instructor_id_15``
     - The ``person_id`` of the remaining teachers.
       The connector only writes as many columns as it needs.

   * - ``location_id``
     - Name of the school.

.. note::

   *Apple School Manager* supports at most 15 teachers per class.
   If a class has more,
   the connector synchronizes the first 15
   and writes a warning to the log file.

.. _synchronization-staff:

Staff
-----

The :file:`staff.csv` file has the columns listed in :numref:`synchronization-staff-table`.
The file holds teachers and teachers with an additional staff role.
The connector doesn't export staff members who don't have a teacher role.

.. _synchronization-staff-table:

.. list-table:: Columns of :file:`staff.csv`
   :header-rows: 1
   :widths: 3 9

   * - Column
     - Source in |UAS|

   * - ``person_id``
     - The attribute from :envvar:`staff.person_id_attribute`,
       ``entryUUID`` by default.

   * - ``person_number``
     - Uses the same value as ``person_id``.

   * - ``first_name``
     - First name of the teacher.

   * - ``middle_name``
     - First value of ``middleName``, ``initials``, or ``oxMiddleName``.

   * - ``last_name``
     - Last name of the teacher.

   * - ``email_address``
     - Primary email address,
       modified by :envvar:`email_prepend_domain`.

   * - ``sis_username``
     - Username of the teacher.

   * - ``location_id``
     - Primary school of the teacher.

   * - ``location_id_2`` and following
     - The other schools of the teacher, in alphabetical order.

.. _synchronization-students:

Students
--------

The :file:`students.csv` file has the columns listed in :numref:`synchronization-students-table`.
The connector doesn't export exam users.

.. FIXME: Duplicate information about the exam users.

.. _synchronization-students-table:

.. list-table:: Columns of :file:`students.csv`
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Source in |UAS|

   * - ``person_id``
     - The attribute from :envvar:`student.person_id_attribute`,
       ``entryUUID`` by default.

   * - ``person_number``
     - Uses the same value as ``person_id``.

   * - ``first_name``
     - First name of the student.

   * - ``middle_name``
     - First value of ``middleName``, ``initials``, or ``oxMiddleName``.

   * - ``last_name``
     - Last name of the student.

   * - ``grade_level``
     - The attribute from :envvar:`student.grade_level_attribute`.
       The field is empty if the attribute is unset.

   * - ``email_address``
     - Primary email address,
       modified by :envvar:`email_prepend_domain`.

   * - ``sis_username``
     - Username of the student.

   * - ``password_policy``
     - The password policy from :envvar:`student.password_policy`.
       See :ref:`configuration-password-policy`.

   * - ``location_id``
     - Primary school of the student.

   * - ``location_id_2`` and following
     - The other schools of the student, in alphabetical order.

.. _synchronization-rosters:

Rosters
-------

The :file:`rosters.csv` file has the columns listed in :numref:`synchronization-rosters-table`.
The file contains only student records.
The ``instructor_id`` columns in :file:`classes.csv` assign teachers to classes.
See :ref:`synchronization-classes`.

.. _synchronization-rosters-table:

.. list-table:: Columns of :file:`rosters.csv`
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Source in |UAS|

   * - ``roster_id``
     - The class name and the ``person_id`` of the student,
       joined with a hyphen.

   * - ``class_id``
     - Name of the school class or work group.

   * - ``student_id``
     - The ``person_id`` of the student.

.. _synchronization-inspect:

Inspect the uploaded data
=========================

To look at what the connector uploads,
enable :envvar:`asm/store_zip` in the app settings
and run the synchronization.
The connector then keeps the archive in :file:`/var/lib/asm/`.

To list and unpack the archive from the most recent upload,
run the commands in :numref:`synchronization-inspect-listing`.

.. code-block:: console
   :caption: List the archives and unpack the newest one
   :name: synchronization-inspect-listing

   $ ls -l /var/lib/asm/
   $ unzip -d /var/tmp/asm "$(ls -t /var/lib/asm/*.zip | head -1)"

.. important::

   The archives contain personal data.
   Delete them when you no longer need them,
   and deactivate :envvar:`asm/store_zip`.
