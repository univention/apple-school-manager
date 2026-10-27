.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _installation:

************
Installation
************

Install the *Apple School Manager Connector* on a supported system role
to synchronize school data with *Apple School Manager*.
Before you start, ensure that you meet the :ref:`introduction-prerequisites`.

.. _installation-system-roles:

Supported system roles
======================

You can install the connector on the following system roles:

* :external+uv-ucs-operation:term:`Primary Directory Node`
* :external+uv-ucs-operation:term:`Backup Directory Node`
* :external+uv-ucs-operation:term:`Replica Directory Node`

On a school Replica Directory Node,
the connector sees only the school of that node.
On a central Replica Directory Node,
a Primary Directory Node, or a Backup Directory Node,
the connector sees every school in the domain.

.. important::

   Install the connector on exactly one system in the domain.

   Each instance uploads a complete data set.
   The upload overwrites the data that the previous instance uploaded.

   Don't install the connector more than once in a domain.
   To synchronize additional schools,
   add them to the existing instance
   as described in :ref:`configuration-school-list`.
   To use another *Apple School Manager* account,
   add it as described in :ref:`configuration-accounts`.

.. _installation-install:

Install the app
===============

Before you begin,
complete the prerequisites in :ref:`introduction-prerequisites`.

To install the *Apple School Manager Connector* app on |UAS|,
follow these steps:

#. Navigate to the *App Center* in :term:`Management UI`
   through :menuselection:`Software --> App Center`.

#. Select :guilabel:`Apple School Manager Connector`.

#. Click :guilabel:`Install`.

#. Wait until the installation completes.

After you install the app,
obtain the credentials as described in :ref:`installation-credentials`
and enter them as described in :ref:`installation-configure-credentials`.

.. seealso::

   :external+uv-ucs-operation:ref:`lifecycle-app-center-installation`
     in :cite:t:`uv-ucs-operation`
     for more information about how to install an app.

   :external+uv-ucs-operation:ref:`lifecycle-app-center`
     in :cite:t:`uv-ucs-operation`
     for more information about Univention App Center.

.. _installation-credentials:

Obtain the SFTP credentials
===========================

*Apple School Manager* generates the SFTP username and password for you.
To find them, do the following:

#. Sign in to `Apple School Manager <https://school.apple.com/>`_.

#. Click your name in the lower-left corner
   and select :guilabel:`Preferences`.

#. Select :guilabel:`Managed Apple Accounts`.

#. Select the menu next to :guilabel:`Apple formatted CSV`,
   and then select :guilabel:`Upload CSV`.

A dialog opens and displays the SFTP username and password.
For background information, see :cite:p:`apple-sftp-upload`.

.. _installation-configure-credentials:

Enter the credentials
=====================

To configure the upload credentials for *Apple School Manager Connector*,
follow these steps:

#. Store the SFTP password that *Apple School Manager* generated
   in :file:`/etc/asm.secret` with permissions set to ``600``,
   as shown in :numref:`installation-configure-credentials-store-listing`.
   Enter the generated SFTP password, save the file, and close the editor.

   .. code-block:: console
      :caption: Store the password
      :name: installation-configure-credentials-store-listing

      $ install -m 600 /dev/null /etc/asm.secret
      $ editor /etc/asm.secret

#. Edit the settings file :file:`/etc/asm-connections.json`,
   which the installation creates without an account.
   Add the SFTP username, path to the password file, and schools.
   For an example, see :numref:`installation-configure-credentials-asm-listing`.

   Replace ``sftp-user`` with the SFTP username that *Apple School Manager*
   generated.
   The entry ``*`` in ``schools`` synchronizes every school to the account.
   Save the file.

   For a detailed description of the settings,
   see :ref:`configuration-file`.
   The configuration page includes information about how to limit the account
   to individual schools, how to add further accounts, and all settings for
   users and classes.

   .. code-block:: json
      :caption: One *Apple School Manager* account in :file:`/etc/asm-connections.json`
      :name: installation-configure-credentials-asm-listing

      {
          "accounts": {
              "main": {
                  "username": "sftp-user",
                  "password_file": "/etc/asm.secret"
              }
          },
          "schools": {
              "*": {"account": "main"}
          }
      }

#. Continue with :ref:`configuration`.
