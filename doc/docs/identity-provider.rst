.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _identity-provider:

*********************************************************
Keycloak as an identity provider for Apple School Manager
*********************************************************

:term:`Apple School Manager` can use an external identity provider
to authenticate sign-ins to *Managed Apple Accounts*.
Your users then sign in to their Apple devices
with the password from your |UAS| domain
instead of a password that *Apple School Manager* manages.

This chapter describes how to set up the :term:`Keycloak` app
in :term:`Nubus for UCS` as that identity provider.

.. caution::

   *Apple School Manager* requires :term:`SSF` support.
   This support is an experimental feature of Keycloak.

.. _identity-provider-ssf:

Why Apple School Manager needs SSF
==================================

The Shared Signals Framework (SSF) is an OpenID Foundation standard.
It supports sharing security events, state changes, and risk signals
between an identity provider and the applications that rely on it.
For more information, see :cite:p:`openid-ssf`.

*Apple School Manager* uses SSF to learn about events in your domain,
such as a changed credential or a revoked session.
It therefore accepts only an identity provider that acts as an SSF transmitter.
A plain :term:`OIDC` client isn't enough.

.. _identity-provider-requirements:

Prerequisites
=============

To use the *Keycloak* app as an identity provider for *Apple School Manager*,
you need to meet the following prerequisites:

* A |UAS| domain
  with the *Apple School Manager* Connector
  and version ``26.7.2-nubus1`` or later of the Keycloak app.

  .. FIXME:  Which Keycloak permissions, command-line host and privileges, and Apple-to-Keycloak network access are required?

* A domain that you verified in *Apple School Manager*.
  For instructions, see :cite:p:`apple-verify-domain`.
  Your users need a primary email address in that domain to sign in.

* An account in *Apple School Manager* with the *Administrator* role
  to connect the identity provider.
  This account can't sign in through the federation itself.
  For instructions, see :cite:p:`apple-roles`.

* An Apple device for the first sign-in.

* Anonymization turned off,
  because *Apple School Manager* needs each user's primary email address
  for their *Apple Account*.
  To turn off anonymization,
  use the settings shown in :numref:`identity-provider-requirements-listing`.

  For more information,
  see :ref:`configuration-anonymization`.

  .. code-block:: json
     :caption: Anonymization settings in :file:`/etc/asm-connections.json` (fragment)
     :name: identity-provider-requirements-listing

     "defaults": {
         "student": {"anonymize": false},
         "staff": {"anonymize": false}
     }

.. _identity-provider-keycloak:

Configure Keycloak
==================

To configure the *Keycloak* app as an identity provider for *Apple School Manager*,
make all changes in the ``ucs`` realm in the *Keycloak Admin Console*.
The ``ucs`` realm contains the users of your domain.

The *Keycloak Admin Console* opens in the ``master`` realm.
Before you change anything, select ``ucs`` in the realm selector.
Check the selected realm whenever you return to the *Keycloak Admin Console*.

.. seealso::

   :external+uv-keycloak-app:ref:`keycloak-admin-console`
      in :cite:t:`uv-keycloak-app`
      for information about how to sign in to the *Keycloak Admin Console*.

.. _identity-provider-keycloak-feature:

Enable the SSF feature
----------------------

Set the app setting
:external+uv-keycloak-app:envvar:`keycloak/server/feature/ssf`
of the Keycloak app to ``true``.
Use the following steps on :term:`Nubus for UCS`:

.. tab-set::

   .. tab-item:: Management UI

      #. Navigate to the *App Center* in :term:`Management UI`
         through :menuselection:`Software --> App Center`.

      #. Open the :guilabel:`Keycloak` app.

      #. Click :guilabel:`App settings`.

      #. Select :guilabel:`keycloak/server/feature/ssf` and set the value to ``true``.

      #. Click :guilabel:`Apply changes`.

   .. tab-item:: Command line

      Alternatively, set the app setting on the command line
      by running the command in :numref:`identity-provider-keycloak-feature-listing`.

      .. code-block:: console
         :caption: Enable the SSF feature of Keycloak
         :name: identity-provider-keycloak-feature-listing

         $ univention-app configure keycloak --set keycloak/server/feature/ssf=true

The App Center then recreates the Keycloak container,
which starts Keycloak with the :term:`SSF` feature.
Keycloak is unavailable for a short time while that happens.

.. note::

   If you set the variable with :command:`ucr set` instead,
   apply it with :command:`univention-app configure keycloak`.
   Restarting the app with :command:`univention-app restart keycloak`
   isn't enough to apply the setting.
   The :guilabel:`Realm settings` page doesn't offer
   :guilabel:`SSF Transmitter`.

   .. FIXME: What does this note mean? What's the action for the reader here?

.. _identity-provider-keycloak-realm:

Turn the realm into an SSF transmitter
--------------------------------------

Activate the :term:`SSF` transmitter in the *Keycloak* app as follows:

#. To open the *Keycloak Admin Console*,
   follow the instructions at
   :external+uv-keycloak-app:ref:`keycloak-admin-console`
   in :cite:t:`uv-keycloak-app`.

#. On the :guilabel:`Realm settings` page,
   set :guilabel:`SSF Transmitter` to :guilabel:`On`.

When the transmitter is active,
the realm offers an SSF configuration metadata endpoint
in addition to the OpenID configuration endpoint.
You need the URLs of the following endpoints
in the :ref:`identity-provider-asm-idp` section.
:samp:`{DOMAIN}` is your Nubus for UCS domain name:

* :samp:`https://ucs-sso-ng.{DOMAIN}/realms/ucs/.well-known/openid-configuration`
* :samp:`https://ucs-sso-ng.{DOMAIN}/realms/ucs/.well-known/ssf-configuration`

The URLs use the defaults of the Keycloak app:
the host :samp:`ucs-sso-ng.{DOMAIN}`
and the realm ``ucs``, which holds the users of the domain.
If you changed
:external+uv-keycloak-app:envvar:`keycloak/server/sso/fqdn`
or use another realm, adjust the URLs accordingly.

.. _identity-provider-keycloak-scopes:

Create the client scopes
------------------------

On the realm's :guilabel:`Client scopes` page,
create the client scopes ``ssf.manage`` and ``ssf.read``,
each with :guilabel:`Include in token scope` enabled.

.. _identity-provider-keycloak-client:

Create the OIDC client
----------------------

To create the OIDC client, follow these steps:

#. On the realm's :guilabel:`Clients` page,
   click :guilabel:`Create client`.

#. On the :guilabel:`General settings` page,
   enter ``apple-asm`` as :guilabel:`Client ID`.

#. On the :guilabel:`Capability config` page,
   enter the settings from :numref:`identity-provider-keycloak-client-table`.

   Apple doesn't appear to support :term:`PKCE` for OIDC federations,
   which is why you turn off the PKCE requirement for the client.

   .. FIXME: An uncertain statement about Apple’s PKCE support is used to justify disabling a security-relevant setting. No documentation exists that confirms the statement.

   To see :guilabel:`SSF Receiver` on the page,
   you need to activate :guilabel:`Client authentication`
   and complete :ref:`identity-provider-keycloak-feature`
   and :ref:`identity-provider-keycloak-realm`.

   .. _identity-provider-keycloak-client-table:

   .. list-table:: Capabilities of the OIDC client for *Apple School Manager*
      :header-rows: 1
      :widths: 4 8

      * - Setting
        - Value

      * - :guilabel:`Client authentication`
        - ``On``

      * - :guilabel:`Authentication flow`
        - ``Standard flow``

      * - :guilabel:`Require PKCE`
        - ``Off``

      * - :guilabel:`SSF Receiver`
        - ``On``

#. On the :guilabel:`Login settings` page,
   enter the settings from :numref:`identity-provider-keycloak-client-login-settings-table`
   and click :guilabel:`Save`.

   .. _identity-provider-keycloak-client-login-settings-table:

   .. list-table:: Login settings of the OIDC client for *Apple School Manager*
      :header-rows: 1
      :widths: 4 8

      * - Setting
        - Value

      * - :guilabel:`Valid redirect URIs`
        - ``https://gsa-ws.apple.com/grandslam/GsService2/acs``

      * - :guilabel:`Valid post logout redirect URIs`
        - ``+``

#. Copy the client secret from the :guilabel:`Credentials` tab.
   You need it in the :ref:`identity-provider-asm-idp` section later.

.. _identity-provider-keycloak-receiver:

Configure the client as an SSF receiver
---------------------------------------

To configure the SSF receiver in the *Keycloak* app,
follow these steps:

#. On the client's :guilabel:`Client scopes` tab,
   add ``ssf.manage``, ``ssf.read``, and ``offline_access``
   as :guilabel:`Default`.

#. On the :guilabel:`Roles` tab,
   add the client role ``ssf-admin``.

#. On the :guilabel:`SSF` tab,
   enter the settings in :numref:`identity-provider-keycloak-receiver-table`.

   * :guilabel:`Auto verify stream` sends the verification event as soon as Apple
     creates the stream.

   * :guilabel:`Emit-only events` lets you control through the Keycloak API when
     Keycloak sends a sign-out to Apple.

.. _identity-provider-keycloak-receiver-table:

.. list-table:: SSF settings of the client
   :header-rows: 1
   :widths: 4 8

   * - Setting
     - Value

   * - :guilabel:`Profile`
     - :guilabel:`SSE CAEP 1.0`

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

   * - :guilabel:`Required role`
     - Click :guilabel:`Select role`,
       select :guilabel:`Client roles`,
       and select ``ssf-admin``.

   * - :guilabel:`Allowed delivery methods`
     - :guilabel:`Push Delivery` only

   * - :guilabel:`Valid push URLs`
     - ``https://federation.apple.com/feeds/school/caep/*``

   * - :guilabel:`Supported Events`
     - ``CaepCredentialChange``, ``CaepSessionRevoked``

   * - :guilabel:`Emit events enabled`
     - :guilabel:`On`

   * - :guilabel:`Emit-only events`
     - ``CaepSessionRevoked``

.. _identity-provider-keycloak-admin-user:

Create the administrative user
------------------------------

*Apple School Manager* establishes the connection to *Keycloak*
with the authorization code flow.
The resulting access token and refresh token
belong to one user's offline session.
That user must exist before you connect the two systems.

Create the user in *Keycloak*, not in Nubus for UCS.
Keycloak has only read access to the users in Nubus for UCS,
so it can't assign client roles to them.
To create an administrative user in *Keycloak*
for *Apple School Manager*,
follow these steps:

#. In the realm ``ucs``,
   create a user, for example ``asm``.

#. Set the first name, the last name, and the email address.

#. On the :guilabel:`Credentials` tab,
   set a strong password.
   Two-factor authentication is optional, but recommended.

#. Assign the client role ``ssf-admin`` of the client ``apple-asm``.

.. _identity-provider-asm:

Configure Apple School Manager
==============================

Configure *Apple School Manager* to use the *Keycloak* app
in Nubus for UCS as an external identity provider.

.. _identity-provider-asm-idp:

Connect the identity provider
-----------------------------

.. FIXME: For the connection, does Apple need access to the identity provider? I suspect, yes.

Connect *Apple School Manager* to the external identity provider:

#. Sign in to `Apple School Manager <https://school.apple.com/>`_.

#. Open :menuselection:`Preferences --> Managed Apple Accounts`.

#. Under :guilabel:`User sign-in and directory sync`,
   click :guilabel:`Configure`.

   If *Apple School Manager* is already connected to another identity provider,
   disconnect it first.

   .. FIXME: What are the consequences of disconnecting an existing connection? We should mention them here.

#. Select :guilabel:`Custom Identity Provider`
   and click :guilabel:`Continue`.

#. Enter a name for the identity provider, for example ``asmkc``.

#. Enter the settings listed in :numref:`identity-provider-asm-idp-table`.
   Use the client ID and client secret from :ref:`identity-provider-keycloak-client`
   and the two URLs from :ref:`identity-provider-keycloak-realm`.

   .. _identity-provider-asm-idp-table:

   .. list-table:: Settings of the custom identity provider in *Apple School Manager*
      :header-rows: 1
      :widths: 2 10

      * - Field
        - Value

      * - :guilabel:`Client ID`
        - ``apple-asm``

      * - :guilabel:`Client Secret`
        - The client secret from the :guilabel:`Credentials` tab of the client

      * - :guilabel:`SSF URL`
        - :samp:`https://ucs-sso-ng.{DOMAIN}/realms/ucs/.well-known/ssf-configuration`

      * - :guilabel:`OIDC URL`
        - :samp:`https://ucs-sso-ng.{DOMAIN}/realms/ucs/.well-known/openid-configuration`

#. Click :guilabel:`Continue`.

#. In the window that opens,
   click the sign-in button for your identity provider,
   for example :guilabel:`Sign in with asmkc`.

#. Sign in with the administrative user from
   :ref:`identity-provider-keycloak-admin-user`.

*Apple School Manager* shows :guilabel:`Authorizing Account`
and then confirms the connection.
During the connection, Apple creates an SSF stream for the client,
which you can see on the client's :guilabel:`SSF Streams` tab in Keycloak.

.. _identity-provider-asm-domain:

Enable federation for the domain
--------------------------------

Enable federation for the domain in *Apple School Manager*:

#. Open :menuselection:`Preferences --> Managed Apple Accounts`.

#. Select your domain and click :guilabel:`Manage`.

#. In the section for your identity provider,
   click :guilabel:`Set up`.

#. Set the toggle that appears to :guilabel:`On`.

#. If the SFTP upload uses the domain,
   *Apple School Manager* asks you to choose another domain for the upload.
   Choose any other domain.

   .. FIXME: The instruction doesn’t explain the requirements for the replacement domain or what to do if none is available. Verify which replacement domains are eligible and what readers must do if none is available.

*Apple School Manager* enables federation for the domain
and sends a confirmation email.

After that, users with a Managed Apple Account whose email address is in the domain
sign in through Keycloak.
This includes users with accounts that existed before you enabled federation
and users with accounts that you created manually in *Apple School Manager*.

.. FIXME: When an administrator manually creates a Managed Apple Account in a federated domain, must a corresponding user exist in Nubus for UCS—and therefore in Keycloak—for the person to sign in? If so, how are the Apple Account and Keycloak user matched?

.. FIXME: Does this apply to accounts created both before and after federation is enabled?

The upload from the connector continues to work.
*Apple School Manager* assigns each account to the domain of its email address,
so the accounts from the upload belong to the federated domain,
regardless of the domain that you chose for the SFTP upload.

.. _identity-provider-onboarding:

Sign in on a device
===================

After you enable federation for the domain,
your users sign in to an Apple device with their |UAS| credentials.
The following steps describe an unpaired device.
See :cite:p:`apple-sign-in` for the general procedure.

.. FIXME: The procedure doesn’t identify the applicable device or operating system, and “unpaired device” is unclear.

#. Open :menuselection:`Settings --> Apple Account`.

#. Tap :guilabel:`Sign In Manually`.

#. Enter the email address of the user in the federated domain
   and tap :guilabel:`Proceed`.

#. The device displays a message with the name of your organization.
   Tap :guilabel:`Proceed`.

#. The Keycloak sign-in page opens with the user name already filled in.
   Enter the password.

#. Enter the device PIN when the device asks for it.

After the sign-in,
:menuselection:`Settings --> Apple Account` shows the user with the email
address from |UAS|.
