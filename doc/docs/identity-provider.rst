.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _identity-provider:

*************************************
Keycloak as identity provider for ASM
*************************************

Apple School Manager can federate the sign-in of its Managed Apple Accounts to
an external identity provider.
Your users then sign in to their Apple devices with the password from your
|UAS| domain
instead of a password that Apple School Manager manages.

This chapter describes how to set up the :term:`Keycloak` app of :term:`UCS`
as that identity provider.

.. caution::

   The :term:`SSF` support that Apple School Manager requires is an
   experimental feature of Keycloak.
   Univention doesn't support this setup in production yet.
   Try it in a test environment first.

.. _identity-provider-ssf:

Why Apple School Manager needs SSF
==================================

The Shared Signals Framework is the standard of the OpenID Foundation for
sharing security events, state changes, and risk signals between an identity
provider and the applications that rely on it.
See :cite:t:`openid-ssf`.

Apple School Manager uses SSF to learn about events in your domain,
such as a changed credential or a revoked session.
It therefore only accepts an identity provider that acts as an SSF transmitter.
A plain :term:`OIDC` client isn't enough.

.. _identity-provider-requirements:

What you need
=============

* A |UAS| domain
  with the Apple School Manager Connector
  and the Keycloak app in version ``26.7.2-nubus1`` or later.

* A domain that you verified in Apple School Manager.
  See :cite:t:`apple-verify-domain`.
  Your users need a primary email address in that domain to sign in.

* An account in Apple School Manager with the *Administrator* role
  to connect the identity provider.
  See :cite:t:`apple-roles`.
  This account can't sign in through the federation itself.

* An Apple device for the first sign-in.

* Anonymization turned off,
  because Apple School Manager needs the email address as the Apple Account:

  .. code-block:: json
     :caption: Turn anonymization off in :file:`/etc/asm-connections.json`

     "defaults": {
         "student": {"anonymize": false},
         "staff": {"anonymize": false}
     }

  See :ref:`configuration-anonymization`.

.. _identity-provider-keycloak:

Configure Keycloak
==================

The app ships the script :command:`asm-setup-keycloak`,
which makes all settings in Keycloak that Apple School Manager needs.
Run it on the Primary Directory Node
or on a Backup Directory Node with the Keycloak app:

.. code-block:: console
   :caption: Set up Keycloak for Apple School Manager

   $ asm-setup-keycloak

The script does the following:

#. It enables the SSF feature of Keycloak, if it isn't enabled yet.
   Keycloak restarts and is unavailable for a short time.

#. It turns the realm ``ucs`` into an SSF transmitter
   and creates the client scopes, the client ``apple-asm``,
   and the client role ``ssf-admin``.

#. It creates the user ``asm`` in Keycloak with the client role ``ssf-admin``
   and asks for the password of the user.
   To pass the password in a file instead,
   use the option ``--password-file``.

Apple School Manager connects to Keycloak with this user.
The script creates it in Keycloak and not in UCS,
because Keycloak has only read access to the UCS users
and can't assign client roles to them.

At the end,
the script prints the values that you need in :ref:`identity-provider-asm-idp`:

.. code-block:: text
   :caption: Output of :command:`asm-setup-keycloak`

   Client ID:     apple-asm
   Client Secret: CLIENT_SECRET
   SSF URL:       https://ucs-sso-ng.DOMAIN/realms/ucs/.well-known/ssf-configuration
   OIDC URL:      https://ucs-sso-ng.DOMAIN/realms/ucs/.well-known/openid-configuration

You can run the script again at any time.
It only changes settings that differ from what Apple School Manager needs,
and it keeps an existing user and its password.
To use other names for the realm, the client, or the user,
see :command:`asm-setup-keycloak --help`.
To check the settings that the script makes,
see :ref:`troubleshooting-keycloak-settings`.

.. _identity-provider-asm:

Configure Apple School Manager
==============================

.. _identity-provider-asm-idp:

Connect the identity provider
-----------------------------

#. Sign in to `Apple School Manager <https://school.apple.com/>`_.

#. Open :menuselection:`Preferences --> Managed Apple Accounts`.

#. Make sure that your domain is verified.

#. Under :guilabel:`User sign-in and directory sync`,
   click :guilabel:`Configure`.
   If another identity provider is connected, disconnect it first.

#. Select :guilabel:`Custom Identity Provider`
   and click :guilabel:`Continue`.

#. Enter a name for the identity provider, for example ``asmkc``.

#. Enter the values that :command:`asm-setup-keycloak` printed,
   as listed in the following table.

   .. list-table:: Settings of the custom identity provider in Apple School Manager
      :header-rows: 1
      :widths: 30 70

      * - Field
        - Value

      * - :guilabel:`Client ID`
        - ``apple-asm``

      * - :guilabel:`Client Secret`
        - The client secret that :command:`asm-setup-keycloak` printed

      * - :guilabel:`SSF URL`
        - ``https://ucs-sso-ng.DOMAIN/realms/ucs/.well-known/ssf-configuration``

      * - :guilabel:`OIDC URL`
        - ``https://ucs-sso-ng.DOMAIN/realms/ucs/.well-known/openid-configuration``

#. Click :guilabel:`Continue`.

#. In the window that opens,
   click the sign-in button for your identity provider,
   for example :guilabel:`Sign in with asmkc`.

#. Sign in with the user ``asm``
   that :command:`asm-setup-keycloak` created.

Apple School Manager shows :guilabel:`Authorizing Account`
and then confirms the connection.
During the connection, Apple creates an SSF stream for the client,
which you can see on the client's :guilabel:`SSF Streams` tab in Keycloak.

.. _identity-provider-asm-domain:

Enable federation for the domain
--------------------------------

#. Open :menuselection:`Preferences --> Managed Apple Accounts`.

#. Select your domain and click :guilabel:`Manage`.

#. At the bottom of the page,
   find the section for your identity provider and click :guilabel:`Set up`.

#. Switch the toggle that appears to :guilabel:`On`.

#. If the SFTP upload uses the domain,
   Apple School Manager asks you to choose another domain for the upload.
   Choose any other domain.

Apple School Manager enables federation for the domain
and sends a confirmation email.

After that, every Managed Apple Account with an email address in the domain
signs in through Keycloak.
This includes accounts that existed before you enabled federation
and accounts that you created manually in Apple School Manager.

The upload from the connector continues to work.
Apple School Manager assigns the accounts by the domain of their email address,
so the accounts from the upload belong to the federated domain,
regardless of the domain that you chose for the SFTP upload.

.. _identity-provider-onboarding:

Sign in on a device
===================

After you enable federation for the domain,
your users sign in to an Apple device with their |UAS| credentials.
The following steps describe an unpaired device.
See :cite:t:`apple-sign-in` for the general procedure.

#. Open :menuselection:`Settings --> Apple Account`.

#. Tap :guilabel:`Sign In Manually`.

#. Enter the email address of the user in the federated domain
   and tap :guilabel:`Proceed`.

#. The device shows a hint that names your organization.
   Tap :guilabel:`Proceed`.

#. The Keycloak sign-in page opens with the user name already filled in.
   Enter the password.

#. Enter the device PIN when the device asks for it.

After the sign-in,
:menuselection:`Settings --> Apple Account` shows the user with the email
address from |UAS|.
