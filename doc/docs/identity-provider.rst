.. SPDX-FileCopyrightText: 2026 Univention GmbH
..
.. SPDX-License-Identifier: AGPL-3.0-only

.. _identity-provider:

*************************************
Keycloak as identity provider for ASM
*************************************

*Apple School Manager* can federate the sign-in of its Managed Apple Accounts to
an external identity provider.
Your users then sign in to their Apple devices with the password from your
|UAS| domain
instead of a password that *Apple School Manager* manages.

This chapter describes how to set up the :term:`Keycloak` app of :term:`Nubus for UCS`
as that identity provider.

.. caution::

   The :term:`SSF` support that *Apple School Manager* requires is an
   experimental feature of Keycloak.

.. _identity-provider-ssf:

Why Apple School Manager needs SSF
==================================

The Shared Signals Framework is the standard of the OpenID Foundation for
sharing security events, state changes, and risk signals between an identity
provider and the applications that rely on it.
See :cite:t:`openid-ssf`.

*Apple School Manager* uses SSF to learn about events in your domain,
such as a changed credential or a revoked session.
It therefore only accepts an identity provider that acts as an SSF transmitter.
A plain :term:`OIDC` client isn't enough.

.. _identity-provider-requirements:

What you need
=============

* A |UAS| domain
  with the *Apple School Manager* Connector
  and the Keycloak app in version ``26.7.2-nubus1`` or later.

* A domain that you verified in *Apple School Manager*.
  See :cite:t:`apple-verify-domain`.
  Your users need a primary email address in that domain to sign in.

* An account in *Apple School Manager* with the *Administrator* role
  to connect the identity provider.
  See :cite:t:`apple-roles`.
  This account can't sign in through the federation itself.

* An Apple device for the first sign-in.

* Anonymization turned off,
  because *Apple School Manager* needs the email address as the Apple Account:

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

Make every setting in the Keycloak admin console in the realm ``ucs``,
which holds the users of your domain.
The admin console opens in the realm ``master``.
Select ``ucs`` in the realm selector before you change anything,
and check the selected realm whenever you return to the admin console.

.. _identity-provider-keycloak-feature:

Enable the SSF feature
----------------------

Set the app setting
:external+uv-keycloak-app:envvar:`keycloak/server/feature/ssf`
of the Keycloak app to ``true``.

#. Open the App Center in :term:`Management UI` and select the Keycloak app.

#. Click :guilabel:`App settings`.

#. Select :guilabel:`keycloak/server/feature/ssf`.

#. Click :guilabel:`Apply changes`.

Alternatively, set it on the command line:

.. code-block:: console
   :caption: Enable the SSF feature of Keycloak

   $ univention-app configure keycloak --set keycloak/server/feature/ssf=true

The App Center then recreates the Keycloak container,
which starts Keycloak with the SSF feature.
Keycloak is unavailable for a short time while that happens.

.. note::

   If you set the variable with :command:`ucr set` instead,
   apply it with :command:`univention-app configure keycloak`.
   Restarting the app with :command:`univention-app restart keycloak`
   isn't enough,
   and the :guilabel:`Realm settings` page doesn't offer
   :guilabel:`SSF Transmitter`.

.. _identity-provider-keycloak-realm:

Turn the realm into an SSF transmitter
--------------------------------------

#. Open the Keycloak admin console at
   ``https://ucs-sso-ng.DOMAIN/admin/``
   and select the realm ``ucs``.
   Replace ``DOMAIN`` with the domain name of your UCS domain.

#. On the :guilabel:`Realm settings` page,
   set :guilabel:`SSF Transmitter` to :guilabel:`On`.

With the transmitter on,
the realm offers an SSF configuration metadata endpoint next to the OpenID
endpoint configuration.
You need the URLs of both endpoints in :ref:`identity-provider-asm-idp`:

* ``https://ucs-sso-ng.DOMAIN/realms/ucs/.well-known/openid-configuration``
* ``https://ucs-sso-ng.DOMAIN/realms/ucs/.well-known/ssf-configuration``

The URLs use the defaults of the Keycloak app:
the host ``ucs-sso-ng.DOMAIN``
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

#. On the realm's :guilabel:`Clients` page,
   click :guilabel:`Create client`.

#. On the :guilabel:`General settings` page,
   enter ``apple-asm`` as :guilabel:`Client ID`.

#. On the :guilabel:`Capability config` page,
   enter the settings from the following table.

   .. list-table:: Capabilities of the OIDC client for *Apple School Manager*
      :header-rows: 1
      :widths: 40 60

      * - Setting
        - Value

      * - :guilabel:`Client authentication`
        - :guilabel:`On`

      * - :guilabel:`Authentication flow`
        - :guilabel:`Standard flow`

      * - :guilabel:`Require PKCE`
        - :guilabel:`Off`

      * - :guilabel:`SSF Receiver`
        - :guilabel:`On`

   Apple doesn't appear to support :term:`PKCE` for OIDC federations,
   which is why the client turns it off.
   The page doesn't offer :guilabel:`SSF Receiver`
   until :guilabel:`Client authentication` is on
   and you completed :ref:`identity-provider-keycloak-feature`
   and :ref:`identity-provider-keycloak-realm`.

#. On the :guilabel:`Login settings` page,
   enter the settings from the following table
   and click :guilabel:`Save`.

   .. list-table:: Login settings of the OIDC client for *Apple School Manager*
      :header-rows: 1
      :widths: 40 60

      * - Setting
        - Value

      * - :guilabel:`Valid redirect URIs`
        - ``https://gsa-ws.apple.com/grandslam/GsService2/acs``

      * - :guilabel:`Valid post logout redirect URIs`
        - ``+``

Copy the client secret from the :guilabel:`Credentials` tab.
You need it in :ref:`identity-provider-asm-idp`.

.. _identity-provider-keycloak-receiver:

Configure the client as an SSF receiver
---------------------------------------

#. On the client's :guilabel:`Client scopes` tab,
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

:guilabel:`Auto verify stream` sends the verification event as soon as Apple
creates the stream.
:guilabel:`Emit-only events` lets you control through the Keycloak API when
Keycloak sends a sign-out to Apple.

.. _identity-provider-keycloak-admin-user:

Create the administrative user
------------------------------

*Apple School Manager* establishes the connection to Keycloak with the
authorization code flow.
The resulting access token and refresh token belong to an offline session of
one user,
so that user must exist before you connect the two systems.

Create the user in Keycloak, not in UCS.
Keycloak has only read access to the UCS users,
so it can't assign client roles to them.

#. In the realm ``ucs``,
   create a user, for example ``asm``.

#. Set the first name, the last name, and the email address.

#. On the :guilabel:`Credentials` tab,
   set a strong password.
   Two-factor authentication is optional but recommended.

#. Assign the client role ``ssf-admin`` of the client ``apple-asm``.

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

#. Enter the client ID and the client secret from
   :ref:`identity-provider-keycloak-client`,
   and the two URLs from :ref:`identity-provider-keycloak-realm`,
   as listed in the following table.

   .. list-table:: Settings of the custom identity provider in *Apple School Manager*
      :header-rows: 1
      :widths: 30 70

      * - Field
        - Value

      * - :guilabel:`Client ID`
        - ``apple-asm``

      * - :guilabel:`Client Secret`
        - The client secret from the :guilabel:`Credentials` tab of the client

      * - :guilabel:`SSF URL`
        - ``https://ucs-sso-ng.DOMAIN/realms/ucs/.well-known/ssf-configuration``

      * - :guilabel:`OIDC URL`
        - ``https://ucs-sso-ng.DOMAIN/realms/ucs/.well-known/openid-configuration``

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

#. Open :menuselection:`Preferences --> Managed Apple Accounts`.

#. Select your domain and click :guilabel:`Manage`.

#. At the bottom of the page,
   find the section for your identity provider and click :guilabel:`Set up`.

#. Switch the toggle that appears to :guilabel:`On`.

#. If the SFTP upload uses the domain,
   *Apple School Manager* asks you to choose another domain for the upload.
   Choose any other domain.

*Apple School Manager* enables federation for the domain
and sends a confirmation email.

After that, every Managed Apple Account with an email address in the domain
signs in through Keycloak.
This includes accounts that existed before you enabled federation
and accounts that you created manually in *Apple School Manager*.

The upload from the connector continues to work.
*Apple School Manager* assigns the accounts by the domain of their email address,
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
