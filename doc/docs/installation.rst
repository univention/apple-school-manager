.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _installation:

************
Installation
************

You install the *Apple School Manager Connector* from the :term:`App Center`,
like any other app.
This chapter describes where you can install it,
how to install it,
and how to obtain the credentials that the connector needs.

.. _installation-system-roles:

Supported system roles
======================

You can install the connector on the following system roles:

* Primary Directory Node
* Backup Directory Node
* Replica Directory Node

.. caution::

   Install the connector on exactly one system in the domain.

   Every installation uploads a complete data set
   and overwrites what the previous upload transferred.
   Two installations therefore overwrite each other's data.
   If you want to synchronize additional schools,
   add them to the existing installation
   as described in :ref:`configuration-school-list`.

On a school Replica Directory Node,
the connector only sees the school of that node.
On a central Replica Directory Node,
a Primary Directory Node, or a Backup Directory Node,
it sees every school in the domain.

.. _installation-install:

Install the app
===============

#. Open the App Center in :term:`UMC`.

#. Select :guilabel:`Apple School Manager Connector`.

#. Click :guilabel:`Install`.

The App Center installs the app
and then opens the app settings,
where you enter the credentials from the next section.

.. note::

   The connector requires UCS\@school in version ``5.2v5`` or later.
   The app refuses to update on a system with an older version.

.. _installation-credentials:

Obtain the SFTP credentials
===========================

Apple School Manager generates the SFTP user name and password for you.
To find them, do the following:

#. Sign in to `Apple School Manager <https://school.apple.com/>`_.

#. Click your name in the lower-left corner
   and select :guilabel:`Preferences`.

#. Select :guilabel:`Managed Apple Accounts`.

#. Open the menu for :guilabel:`Apple formatted CSV`.

#. Click :guilabel:`Upload CSV`.

A new frame opens and shows the SFTP account data.
For background information, see :cite:t:`apple-sftp-upload`.

.. _installation-configure-credentials:

Enter the credentials
=====================

#. Open the App Center in UMC and select the app.

#. Click :guilabel:`App settings`.

#. Enter the user name in the :guilabel:`asm/username` field
   and the password in the :guilabel:`asm/password` field.

#. Click :guilabel:`Apply changes`.

The connector stores the password in :file:`/etc/asm.secret`
with read permission for the ``root`` user only.

After you've saved the settings,
continue with :ref:`configuration`.
