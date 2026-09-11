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
UCS\@school domain
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

* A UCS\@school domain
  with the Apple School Manager Connector
  and the Keycloak app in version ``26.7.1`` or later.

* A domain that you verified in Apple School Manager.
  See :cite:t:`apple-verify-domain`.
  Your users need a primary email address in that domain to sign in.

* An Apple device for the first sign-in.

* Anonymization turned off,
  because Apple School Manager needs the email address as the Apple Account:

  .. code-block:: console
     :caption: Turn anonymization off

     $ ucr set asm/attributes/student/anonymize=false
     $ ucr set asm/attributes/staff/anonymize=false

  See :ref:`configuration-anonymization`.

.. _identity-provider-keycloak:

Configure Keycloak
==================

.. _identity-provider-keycloak-feature:

Enable the SSF feature
----------------------

Set the app setting ``keycloak/server/feature/ssf`` of the Keycloak app.

.. _identity-provider-keycloak-realm:

Turn the realm into an SSF transmitter
--------------------------------------

#. Open the Keycloak admin console and select your realm.

#. On the :guilabel:`Realm settings` page,
   set :guilabel:`SSF Transmitter` to :guilabel:`On`.

The realm now offers an SSF configuration metadata endpoint next to the OpenID
endpoint configuration.
You need the URL of both endpoints in :ref:`identity-provider-asm-idp`:

* :samp:`https://{keycloak.example.com}/realms/{realm}/.well-known/openid-configuration`
* :samp:`https://{keycloak.example.com}/realms/{realm}/.well-known/ssf-configuration`

.. _identity-provider-keycloak-scopes:

Create the client scopes
------------------------

Create the client scopes ``ssf.manage`` and ``ssf.read``,
each with :guilabel:`Include in token scope` enabled.

.. _identity-provider-keycloak-client:

Create the OIDC client
----------------------

Create a client with the following settings.

.. list-table:: Settings of the OIDC client for Apple School Manager
   :header-rows: 1
   :widths: 40 60

   * - Setting
     - Value

   * - :guilabel:`Client ID`
     - ``apple-asm``

   * - :guilabel:`Client authentication`
     - :guilabel:`On`

   * - :guilabel:`Authentication flow`
     - :guilabel:`Standard flow`

   * - :guilabel:`Valid redirect URIs`
     - ``https://gsa-ws.apple.com/grandslam/GsService2/acs``

   * - :guilabel:`Valid post logout redirect URIs`
     - ``+``

   * - :guilabel:`PKCE`
     - :guilabel:`Off`

Apple doesn't appear to support :term:`PKCE` for OIDC federations,
which is why the client turns it off.

Copy the client secret from the :guilabel:`Credentials` tab.
You need it in :ref:`identity-provider-asm-idp`.

.. _identity-provider-keycloak-receiver:

Configure the client as an SSF receiver
---------------------------------------

#. On the client's :guilabel:`Settings` tab,
   set :guilabel:`SSF Receiver` to :guilabel:`On`.

#. On the :guilabel:`Client scopes` tab,
   add ``ssf.manage``, ``ssf.read``, and ``offline_access``
   as :guilabel:`Default`.

#. On the :guilabel:`Roles` tab,
   add the client role ``ssf-admin``.

#. On the :guilabel:`SSF` tab,
   enter the settings from the following table.

.. list-table:: SSF settings of the client
   :header-rows: 1
   :widths: 40 60

   * - Setting
     - Value

   * - :guilabel:`Profile`
     - ``SSE CAEP 1.0``

   * - :guilabel:`Default Subjects`
     - ``NONE``

   * - :guilabel:`Subject format`
     - ``iss_sub``

   * - :guilabel:`Add subject on login`
     - :guilabel:`On`

   * - :guilabel:`Auto verify stream`
     - :guilabel:`On`

   * - :guilabel:`Verification delay`
     - ``1500``

   * - :guilabel:`Required Client Role`
     - ``apple-asm`` / ``ssf-admin``

   * - :guilabel:`Allowed delivery methods`
     - ``Push Delivery`` only

   * - :guilabel:`Valid push URLs`
     - ``https://federation.apple.com/feeds/school/caep/*``

   * - :guilabel:`Supported Events`
     - ``CaepCredentialChange``, ``CaepSessionRevoked``

   * - :guilabel:`Emit events enabled`
     - :guilabel:`On`

   * - :guilabel:`Emit-only events`
     - ``CaepSessionRevoked``

:guilabel:`Auto verify stream` sends the verification event as soon as Apple
creates the stream.
:guilabel:`Emit-only events` lets you control through the API when the
connector propagates a sign-out.

.. _identity-provider-keycloak-admin-user:

Create the administrative user
------------------------------

Apple School Manager establishes the connection to Keycloak with the
authorization code flow.
The resulting access token and refresh token belong to an offline session of
one user,
so that user must exist before you connect the two systems.

#. Create a user, for example ``asm``.

#. Set the first name, the last name, and the email address.

#. On the :guilabel:`Credentials` tab,
   set a strong password.
   Two-factor authentication is optional but recommended.

#. Assign the client role ``apple-asm`` / ``ssf-admin``.

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
   click :guilabel:`Connect`.
   If another identity provider is connected, disconnect it first.

#. Select :guilabel:`Custom Identity Provider`
   and click :guilabel:`Continue`.

#. Enter a name for the identity provider, for example ``asmkc``.

#. Enter the client ID, the client secret,
   the SSF configuration URL,
   and the OpenID configuration URL from
   :ref:`identity-provider-keycloak-realm`.

#. Click :guilabel:`Continue`.

#. In the window that opens, click :guilabel:`Sign in with asmkc`.

#. Sign in with the administrative user from
   :ref:`identity-provider-keycloak-admin-user`.

Apple School Manager shows :guilabel:`Authorizing Account`
and then confirms the connection.
Apple has now created an SSF stream for the client,
which you can see on the client's :guilabel:`SSF Streams` tab in Keycloak.

.. _identity-provider-asm-domain:

Enable federation for the domain
--------------------------------

#. Open :menuselection:`Preferences --> Managed Apple Accounts`.

#. Select your domain and click :guilabel:`Manage`.

#. At the bottom of the page,
   find the section for your identity provider and click :guilabel:`Set up`.

#. Switch the toggle that appears to :guilabel:`On`.

Federation is now active for the domain,
and Apple School Manager sends a confirmation email.

.. _identity-provider-onboarding:

Sign in on a device
===================

Your users can now sign in to an Apple device with their UCS\@school
credentials.
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

:menuselection:`Settings --> Apple Account` now shows the user with the email
address from UCS\@school.
