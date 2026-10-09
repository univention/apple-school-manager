.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _introduction:

************
Introduction
************

The *Apple School Manager Connector* is an app for :term:`UCS@school`.
It provisions the schools, classes, work groups, teachers, and students of your
|UAS| domain to :term:`Apple School Manager`,
so that you don't have to maintain the same accounts twice.

In this setup, |UAS| takes the role of the student information system
that Apple School Manager expects,
and the connector uses the SFTP interface that Apple provides for such systems.
The connector collects the data from the LDAP directory,
writes it to a set of CSV files,
packs them into a ZIP archive,
and uploads that archive to Apple School Manager.

.. _introduction-audience:

Who this documentation is for
=============================

This documentation addresses administrators
who run a |UAS| domain
and who want to provision its users to Apple School Manager.
It assumes that you're familiar with the administration of
:term:`UCS` and |UAS|,
in particular with the following topics:

* The :term:`App Center`,
  see :ref:`uv-manual:software-appcenter`
  in the UCS manual :cite:p:`ucs-manual`.

* The :term:`UCR`,
  see :ref:`uv-manual:computers-administration-of-local-system-configuration-with-univention-configuration-registry`
  in the UCS manual :cite:p:`ucs-manual`.

* The school objects that |UAS| manages,
  see :ref:`uv-ucsschool-manual:structure-ldap`
  in the |UAS| manual :cite:p:`ucsschool-manual`,
  which is available only in German.

.. _introduction-prerequisites:

What you need
=============

Before you start, make sure that you have the following:

* A |UAS| domain with at least one school.

* An Apple School Manager account for an educational institution.

* The SFTP credentials for the Apple School Manager account.
  :ref:`installation-credentials` describes where to find them.

* A primary email address for each user.
  Apple School Manager uses the email address as the Apple Account
  and can't create an account for a user without one.

.. _introduction-scope:

What the connector synchronizes
===============================

The connector transfers data in one direction only, from |UAS| to Apple
School Manager.
It never reads data back,
and it never changes objects in your |UAS| domain.

The following table lists what the connector maps to which Apple School Manager
entity.

.. list-table:: Objects that the connector synchronizes
   :header-rows: 1
   :widths: 40 60

   * - |UAS| object
     - Apple School Manager entity

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

Apple School Manager requires every class to belong to a course,
so the connector turns each school class and work group into a course
with exactly one class in it.
See :ref:`synchronization-courses`.

Staff members without a teacher role aren't synchronized.
Exam users aren't synchronized either.

:ref:`synchronization` describes the mapping in detail,
including the individual CSV columns.

.. _introduction-passwords:

Passwords and devices
=====================

The connector never transfers passwords.
Apple School Manager creates the passwords for new accounts itself,
and you distribute them from there.
:ref:`configuration-password-policy` describes how to influence the length of
those passwords.

For device management, Univention recommends a mobile device management
solution that offers an interface to Apple School Manager.
The `Univention integration catalog
<https://www.univention.com/products/integration-catalog/>`_
lists the solutions that integrate with |UAS|.
