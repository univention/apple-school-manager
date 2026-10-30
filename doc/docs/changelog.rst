.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _changelog:

*********
Changelog
*********

This chapter lists the changes of every released version of the app.

.. _changelog-v6.0.0:

v6.0.0 (2026-10-19)
===================

* The connector synchronizes to several *Apple School Manager* accounts.
  Each account receives only the schools that you assign to it.

* The settings file :file:`/etc/asm-connections.json` replaces the app
  settings ``asm/username``, ``asm/password``, and ``asm/school_whitelist``
  and all ``asm/attributes/*`` and ``asm/ldap_filter/*`` UCR variables.
  The settings for students and teachers apply per account,
  the settings for classes and the LDAP filters per school.
  The update moves the former values to the new file,
  as described in
  :ref:`Update from an earlier version <configuration-accounts-migration>`.

* An error during the upload to one account,
  for example an invalid LDAP filter,
  only stops the upload to that account.

* :samp:`asm/last_upload/{ACCOUNT}` holds the time of the last upload to each account.

* The connector no longer checks whether the domain of an email address
  resolves.
  The check only wrote a warning,
  and *Apple School Manager* accepts such addresses.

* The app supports Keycloak as identity provider for *Apple School Manager*.
  Users sign in to their *Managed Apple Accounts*
  with the password from the |UAS| domain.
  See :ref:`identity-provider`.

.. _changelog-v5.1.1:

v5.1.1 (2026-03-05)
===================

* The connector supports running on a central :external+uv-ucs-operation:term:`Replica Directory Node` again.

.. _changelog-v5.1.0:

v5.1.0
======

* The connector exports more additional locations for students and teachers.

.. _changelog-v5.0.3:

v5.0.3
======

* The app refuses installation on a central :external+uv-ucs-operation:term:`Replica Directory Node`.

.. _changelog-v5.0.2:

v5.0.2
======

* Follow-up release for version 5.0.1.
  A mismatched component ID in the App Center prevented the update from
  UCS 5.0.

.. _changelog-v5.0.1:

v5.0.1
======

* First release for |UAS| 5.2.
  Functionally identical to version 3.0.3.

.. _changelog-v4.0.0:

v4.0.0
======

* First release for |UAS| 5.1.
  Functionally identical to version 3.0.3.

.. _changelog-v3.0.3:

v3.0.3
======

* Fixed a Debian dependency.

.. _changelog-v3.0.2:

v3.0.2
======

* The connector exports the grade level,
  configured with ``asm/attributes/student/grade_level``.

.. _changelog-v3.0.1:

v3.0.1
======

* The log rotation of the connector follows the ``logrotate/*`` UCR variables.

.. _changelog-v2.2.4:

v2.2.4
======

* The connector applies configured LDAP filters correctly when it loads
  classes.

.. _changelog-v2.2.3:

v2.2.3
======

* Fixed the handling of unexpected errors.

.. _changelog-v2.2.2:

v2.2.2
======

* The name of a course,
  which the connector derives from the school class,
  follows the pattern in ``asm/attributes/course-name-pattern``.
  The default is ``{ou}-{name}``.

.. _changelog-v2.2.1:

v2.2.1
======

* The connector applies configured LDAP filters to :file:`rosters.csv`.

.. _changelog-v2.2.0:

v2.2.0
======

* The connector uses the name of the school class as the course name.
  It used the description of the school class before.

* LDAP filters give you finer control over the exported teachers and students.
  Set them globally or per school with ``asm/ldap_filter/students`` and
  ``asm/ldap_filter/staff``.
  An invalid filter stops the synchronization without an export.

.. _changelog-v2.1.0:

v2.1.0
======

* The connector fills the ``password_policy`` column for new students from
  ``asm/attributes/student/password_policy``.

.. _changelog-v2.0.0:

v2.0.0
======

* First release for UCS 4.4.
  Functionally identical to version 1.2.

.. _changelog-v1.2.0:

v1.2.0
======

* The connector handles classes with more than 15 teachers correctly.
  It exports 15 of them,
  which is the limit of *Apple School Manager*.

.. _changelog-v1.1.0:

v1.1.0
======

* You can install the app on a Replica Directory Node.

.. _changelog-v1.0.0:

v1.0.0
======

* First release.
