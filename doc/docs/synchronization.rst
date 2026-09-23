.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _synchronization:

***************
Synchronization
***************

A synchronization run reads the school data from the LDAP directory,
writes it to CSV files,
packs the files into a ZIP archive,
and uploads the archive to Apple School Manager.
This chapter describes the run itself
and the data that it transfers.

.. _synchronization-run:

Run the synchronization
=======================

Three things start a synchronization run:

* The cron job from :ref:`configuration-schedule`.

* Saving the app settings,
  if you enabled ``asm/run_on_appsetting_save``.

* The command :command:`asm-upload` on the command line.

.. code-block:: console
   :caption: Start a synchronization run manually

   $ /usr/sbin/asm-upload

The command writes progress messages to the terminal
and a more detailed log to :file:`/var/log/univention/asm.log`.
It exits with a non-zero status
if the credentials are missing
or if the upload to any account fails.

.. _synchronization-run-steps:

What happens during a run
-------------------------

#. The connector reads the accounts from :file:`/etc/asm-connections.json`,
   as described in :ref:`configuration-accounts`.
   A missing or invalid entry stops the run.

#. The connector collects the schools, classes, work groups, teachers, and
   students from the LDAP directory,
   restricted by the ``school_whitelist`` of the account
   and by the LDAP filters from :ref:`configuration-ldap-filter`.

#. The connector writes the six CSV files from
   :ref:`synchronization-csv-files` to a temporary directory.

#. The connector packs the CSV files into
   :file:`/var/lib/asm/asm_TIMESTAMP.zip`
   and removes the temporary directory.
   ``TIMESTAMP`` is the time the connector created the archive,
   in ISO 8601 format,
   for example ``2026-10-01T03:00:12.345678``.

#. The connector opens an SFTP connection to
   ``upload.appleschoolcontent.com``
   and uploads the archive as :file:`archive.zip`.
   It verifies the host key against :file:`/etc/asm_public_key`.

#. The connector sets ``asm/last_upload`` to the current time
   and deletes the archive,
   unless you enabled ``asm/store_zip``.

With several accounts,
the connector repeats the steps 2 to 6 for each account.

Every run transfers the complete data set.
The connector doesn't track what changed since the last run.

.. _synchronization-lifecycle:

How Apple School Manager applies the data
-----------------------------------------

Apple School Manager compares the uploaded data with the accounts that it
holds:

* A user who appears for the first time gets a new account.

* A user who is no longer in the upload is deactivated immediately
  and deleted after 30 days.

* A user whose attributes changed keeps the account,
  as long as the ``person_id`` column is unchanged.
  See :ref:`configuration-person-id`.

.. _synchronization-csv-files:

The CSV files
=============

The archive contains the following six files.
Apple documents their format in :cite:t:`apple-sis-csv`.
The connector sorts the rows of each file by school and then by user or class
name.

.. list-table:: Files in the uploaded archive
   :header-rows: 1
   :widths: 25 75

   * - File
     - Content

   * - :file:`locations.csv`
     - One row per school.

   * - :file:`courses.csv`
     - One row per school class and work group.

   * - :file:`classes.csv`
     - One row per school class and work group,
       with the teachers of that class.

   * - :file:`staff.csv`
     - One row per teacher.

   * - :file:`students.csv`
     - One row per student.

   * - :file:`rosters.csv`
     - One row per membership of a student in a school class or work group.

.. _synchronization-locations:

Locations
---------

.. list-table:: Columns of :file:`locations.csv`
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Source in UCS\@school

   * - ``location_id``
     - Name of the school, for example ``gym123``.

   * - ``location_name``
     - Display name of the school.
       Falls back to the name if the school has no display name.

.. _synchronization-courses:

Courses
-------

Apple School Manager requires every class to belong to a course.
UCS\@school only has the school class or work group,
so the connector exports each of them twice:
once as a course in :file:`courses.csv`
and once as a class of that course in :file:`classes.csv`.
Both rows use the name of the group as their ID,
so each course has exactly one class.

.. list-table:: Columns of :file:`courses.csv`
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Source in UCS\@school

   * - ``course_id``
     - Name of the school class or work group,
       including the school prefix, for example ``gym123-1a``.

   * - ``course_number``
     - Same value as ``course_id``.

   * - ``course_name``
     - Built from ``asm/attributes/course-name-pattern``.
       See :ref:`configuration-course-names`.

   * - ``location_id``
     - Name of the school.

.. _synchronization-classes:

Classes
-------

.. list-table:: Columns of :file:`classes.csv`
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Source in UCS\@school

   * - ``class_id``
     - Name of the school class or work group.

   * - ``class_number``
     - Empty by default.
       See ``asm/attributes/classes/class_number_empty`` in
       :ref:`configuration-course-names`.

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

   Apple School Manager supports at most 15 teachers per class.
   If a class has more,
   the connector synchronizes the first 15
   and writes a warning to the log file.

.. _synchronization-staff:

Staff
-----

.. list-table:: Columns of :file:`staff.csv`
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Source in UCS\@school

   * - ``person_id``
     - The attribute from ``asm/attributes/staff/person_id/mapping``,
       ``entryUUID`` by default.

   * - ``person_number``
     - Same value as ``person_id``.

   * - ``first_name``
     - First name of the teacher.

   * - ``middle_name``
     - First value of ``middleName``, ``initials``, or ``oxMiddleName``.

   * - ``last_name``
     - Last name of the teacher.

   * - ``email_address``
     - Primary email address,
       modified by ``asm/attributes/user/email/prepend_domain``.

   * - ``sis_username``
     - User name of the teacher.

   * - ``location_id``
     - Primary school of the teacher.

   * - ``location_id_2`` and following
     - The other schools of the teacher, in alphabetical order.

The file holds teachers and teachers with an additional staff role.
Staff members without a teacher role aren't part of the export.

.. _synchronization-students:

Students
--------

.. list-table:: Columns of :file:`students.csv`
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Source in UCS\@school

   * - ``person_id``
     - The attribute from ``asm/attributes/student/person_id/mapping``,
       ``entryUUID`` by default.

   * - ``person_number``
     - Same value as ``person_id``.

   * - ``first_name``
     - First name of the student.

   * - ``middle_name``
     - First value of ``middleName``, ``initials``, or ``oxMiddleName``.

   * - ``last_name``
     - Last name of the student.

   * - ``grade_level``
     - The attribute from ``asm/attributes/student/grade_level``.
       Empty if the variable is unset.

   * - ``email_address``
     - Primary email address,
       modified by ``asm/attributes/user/email/prepend_domain``.

   * - ``sis_username``
     - User name of the student.

   * - ``password_policy``
     - The value of ``asm/attributes/student/password_policy``.
       See :ref:`configuration-password-policy`.

   * - ``location_id``
     - Primary school of the student.

   * - ``location_id_2`` and following
     - The other schools of the student, in alphabetical order.

Exam users aren't part of the export.

.. _synchronization-rosters:

Rosters
-------

.. list-table:: Columns of :file:`rosters.csv`
   :header-rows: 1
   :widths: 30 70

   * - Column
     - Source in UCS\@school

   * - ``roster_id``
     - The class name and the ``person_id`` of the student,
       joined with a hyphen.

   * - ``class_id``
     - Name of the school class or work group.

   * - ``student_id``
     - The ``person_id`` of the student.

The file only holds students.
Teachers reach a class through the ``instructor_id`` columns of
:file:`classes.csv`.

.. _synchronization-inspect:

Inspect the uploaded data
=========================

To look at what the connector uploads,
enable ``asm/store_zip`` in the app settings
and run the synchronization.
The connector then keeps the archive in :file:`/var/lib/asm/`.

.. code-block:: console
   :caption: List the archives and unpack the newest one

   $ ls -l /var/lib/asm/
   $ unzip -d /var/tmp/asm "$(ls -t /var/lib/asm/*.zip | head -1)"

.. caution::

   The archives contain personal data.
   Delete them when you no longer need them,
   and turn ``asm/store_zip`` off again.
