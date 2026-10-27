.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _introduction:

************
Introduction
************

The *Apple School Manager Connector* is an app for :term:`UCS@school`.
It provisions the information about schools, classes, work groups, teachers, and students
of your |UAS| domain to :term:`Apple School Manager`,
so that you don't have to maintain the same accounts twice.

In this setup, |UAS| acts as the student information system
for *Apple School Manager*.
The connector uses the SFTP interface that Apple provides
for student information systems.
It collects data from the LDAP directory and writes it to CSV files.
It then packs the files into a ZIP archive
and uploads the archive to *Apple School Manager*.

.. _introduction-audience:

Audience
========

Use this documentation if you administer a |UAS| domain
and want to provision its users to *Apple School Manager*.

.. _introduction-prerequisites:

Prerequisites
=============

Before you start, make sure that you have the following:

* A |UAS| domain with at least one school.

* The system runs |UAS| version ``5.2v5`` or later.

* An *Apple School Manager* account for an educational institution.

* The SFTP credentials for the *Apple School Manager* account.

  For information about how to obtain the credentials,
  see :ref:`installation-credentials`.

* A primary email address for each user.

  *Apple School Manager* uses the email address as the Apple Account
  and can't create an account for a user without one.

You need to be familiar with administering :term:`Nubus for UCS` and |UAS|,
including the following topics:

* The :term:`App Center`,
  see :external+uv-ucs-operation:ref:`lifecycle-app-center`
  in :cite:t:`uv-ucs-operation`.

* The :term:`UCR`,
  see :external+uv-ucs-operation:ref:`system-administration-ucr`
  in :cite:t:`uv-ucs-operation`.

* The school objects that |UAS| manages,
  see :external+uv-ucsschool-manual:ref:`structure-ldap`
  in :cite:t:`ucsschool-manual`,
  which is available only in German.

.. _introduction-synchronized-objects:

Objects that the connector synchronizes
=======================================

The connector transfers data in one direction only,
from |UAS| to *Apple School Manager*.
It never writes data back,
and it never changes objects in your |UAS| domain.

:numref:`introduction-object-mapping-table` lists
which objects the connector maps to which *Apple School Manager* entity.

*Apple School Manager* requires every class to belong to a course,
so the connector turns each school class and work group into a course
with exactly one class in it.
For more information,
see :ref:`synchronization-courses`.

.. _introduction-object-mapping-table:

.. list-table:: Objects that the connector synchronizes
   :header-rows: 1
   :widths: 8 4

   * - |UAS| object
     - *Apple School Manager* entity

   * - School
     - Location

   * - School class or work group
     - Course and class

   * - Student
     - Student

   * - Teacher and teacher with staff role
     - Staff member

   * - Membership of a student in a school class or work group
     - Roster entry

.. _introduction-unsynchronized-objects:

Objects that the connector doesn't synchronize
==============================================

The connector doesn't synchronize the following objects:

* Staff members who don't have a teacher role
* Exam users

For detailed information about the mapping,
including the individual CSV columns,
see :ref:`synchronization`.

.. _introduction-passwords:

Passwords
=========

The connector never transfers passwords.
*Apple School Manager* creates the initial passwords for new accounts.
Distribute the passwords from *Apple School Manager*.
For information about how to configure the password length,
see :ref:`configuration-password-policy`.

.. _introduction-device-management:

Device management
=================

For device management, use a mobile device management solution
that integrates with *Apple School Manager*.
For a list of solutions that integrate with |UAS|,
see the `Univention integration catalog <https://www.univention.com/products/integration-catalog/>`_
and confirm that the selected solution integrates with *Apple School Manager*.
