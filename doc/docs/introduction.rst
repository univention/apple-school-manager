.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _introduction:

************
Introduction
************

The *Apple School Manager Connector* is an app for :term:`UCS@school`.
It provisions the schools, classes, work groups, teachers, and students of your
UCS\@school domain to :term:`Apple School Manager`,
so that you don't have to maintain the same accounts twice.

In this setup, UCS\@school takes the role of the student information system
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
who run a UCS\@school domain
and who want to provision its users to Apple School Manager.
It assumes that you're familiar with the administration of
:term:`UCS` and UCS\@school,
in particular with the :term:`App Center`,
the :term:`UCR`,
and the school objects that UCS\@school manages.

.. _introduction-prerequisites:

What you need
=============

Before you start, make sure that you have the following:

* A UCS\@school domain with at least one school.

* An Apple School Manager account for an educational institution.

* The SFTP credentials for the Apple School Manager account.
  :ref:`installation-credentials` describes where to find them.

* A primary email address for each user.
  Apple School Manager uses the email address as the Apple Account
  and can't create an account for a user without one.

.. _introduction-scope:

What the connector synchronizes
===============================

The connector transfers data in one direction only, from UCS\@school to Apple
School Manager.
It never reads data back,
and it never changes objects in your UCS\@school domain.

The following table lists what the connector maps to which Apple School Manager
entity.

.. list-table:: Objects that the connector synchronizes
   :header-rows: 1
   :widths: 40 60

   * - UCS\@school object
     - Apple School Manager entity

   * - School
     - Location

   * - School class or work group
     - One course and one class of that course

   * - Student
     - Student

   * - Teacher and teacher with staff role
     - Staff member

   * - Membership of a student in a school class or work group
     - Roster entry

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
lists the solutions that integrate with UCS\@school.
