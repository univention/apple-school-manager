# Requirements

* UCS + ASM Connector + Keycloak App
  * `ucr set asm/attributes/student/anonymize=false` for emails to be transmitted, we need those as apple id
  * `ucr set asm/attributes/staff/anonymize=false` for emails to be transmitted, we need those as apple id
* A verified domain in ASM
* A apple device for the initial onboarding

# Keycloak image

* as long as the SSF feature is not part of the nubus keycloak image, we need to ...
* got to keycloak-app repo
* download keycloak nightly build keycloak-999.0.0-SNAPSHOT.tar.gz
* build container locally `docker buildx build docker/keycloak --build-arg KEYCLOAK_VERSION=999.0.0-SNAPSHOT -t nightly-keycloak --no-cache`
* export image to archive `docker save -o night-image.tar nightly-keycloak:latest`
* copy archive to UCS server
* on the UCS server
  * import image `docker load -i night-image.tar`
  * in `/var/cache/univention-appcenter/appcenter.software-univention.de/5.0/keycloak_20260226143602.compose` (or whatever keycloak version is installed)
    * replace `image*` with `image: "nightly-keycloak:latest"`
    * add `--spi-datastore-legacy-allow-migrate-existing-database-to-snapshot=true --feature-ssf enabled --spi-events-listener-jboss-logging-success-level=info --spi-events-listener-jboss-logging
-error-level=warn --log-level=info,org.keycloak.ssf:trace` to "command"
  * run `univention-app reinitialize keycloak`

# Setup UCS keycloak

## Realm

* In Realm Settings, set **SSF Transmitter** to **On**.
* Copy the SSF configuration URL: `https://site/realms/ssf-poc/.well-known/ssf-configuration`
* Copy the OpenID configuration URL: `https://site/realms/ssf-poc/.well-known/openid-configuration`

## OIDC client for ASM

* Create a OIDC client:
* Client ID: `apple-asm`
* Client Authentication: **On**
* Authentication Flow: **Standard Flow** enabled
* Valid redirect URIs: `https://gsa-ws.apple.com/grandslam/GsService2/acs/*` (or https://gsa-ws.apple.com/grandslam/GsService2/acs)
* Valid post logout redirect URIs: `+`
* PKCE: **Off** (Apple currently does not appear to support PKCE for OIDC federations)
* Copy the client secret from the **Credentials** tab.

## Client scopes

* create client scopes `ssf.manage`, `ssf.read` with `Include in token scope`

## Configure SSF Receiver support for the client

* Configure SSF Receiver support for the client:
  * **SSF Receiver**: **On**
  * In the **Client Scopes** tab, add `ssf.manage`, `ssf.read`, and `offline_access` as **Default**.
  * Add the client role `ssf-admin` (required for the ASM admin user).
* Configure the SSF Receiver:
  * Open the client's **SSF** tab.
  * Set **Profile** to `SSE CAEP 1.0`.
  * **Default Subjects**: `NONE`
  * **Subject format**: `iss_sub`
  * **Add subject on login**: **On**
  * **Auto verify stream**: **On** (sends the verification event immediately after Apple creates the stream).
  * **Verification delay**: `1500`
  * **Required Client Role**: `apple-asm` @ `ssf-admin`
  * **Allowed delivery methods**: `Push Delivery`, deactivate `Poll delivery`
  * **Valid push URLs**: `https://federation.apple.com/feeds/school/caep/*`
  * **Supported Events**: `CaepCredentialChange`, `CaepSessionRevoked`
  * **Emit events enabled**: **On**
  * **Emit-only events**: `CaepSessionRevoked` (lets you control when user sign-outs are propagated via API).

## ASM admin user

This user is used to establish the ASM to Keycloak connection via the Authorization Code Flow, producing an access/refresh token bound to an offline user session.
* Create a user, e.g. username `asm`, and complete the profile as needed.
* In **Credentials**, configure a strong password and 2FA (this is the Apple integration user, but optional).
* Assign the client role `apple-asm/ssf-admin`.
* Set firstname, lastname and email

# ABM Setup

## IDP setup

* Go to https://school.apple.com and login
* Navigate to **Preferences->Managed Apple Accounts**.
* Add domain and Ensure your domain (e.g. `your-domain.com`) is verified. See: https://support.apple.com/guide/business/verify-a-domain-axm48c3280c0/web. UCS Users need a primary email address with that domain in order to login!
* Set up Keycloak as an Identity Provider:
  * Under **User sign-in and directory sync**, click **Connect** or disconnect current IDP
  * Select **Custom Identity Provider** and **Continue**.
  * Enter a name, e.g. `asmkc`.
  * **Client ID**: your client id, e.g. `apple-asm`
  * **Client Secret**: your client secret
  * **SSF URL**: the SSF configuration URL, e.g. `https://site/realms/ssf-poc/.well-known/ssf-configuration`
  * **OIDC URL**: the OpenID configuration URL, e.g. `https://site/realms/ssf-poc/.well-known/openid-configuration`
  * Click **Continue**.
  * After a few seconds a new window appears with a **Sign in with asmkc** button.
  * Click **Sign in with asmkc**.
  * A Keycloak login page opens in a new window.
  * Sign in with the AsM admin user.
  * You should see an **Authorizing Account** message.
  * On success, an **asmkc connected** confirmation is shown.

At this point, Apple has created an SSF stream for the `apple-asm` SSF receiver OIDC client. The stream is visible in the client's **SSF Streams** tab.

## Connect IDP to domain

* Navigate to **Preferences->Managed Apple Accounts**.
* Select your target domain and click **Manage**.
* At the bottom of the page, find the **Sign In with abmkc** section and click **Set up**.
* After a few seconds a toggle appears â€” switch it to **On**.

Federation is now enabled for your domain. The ABM account should receive a **Federation Enabled** confirmation email.

# Onboarding a User via Device

Users can now onboard their Apple devices via Keycloak. The following describes
the flow for an unpaired device.

See: https://support.apple.com/guide/iphone/sign-in-and-manage-your-apple-account-iph76e54c61e/ios

- Open **Settings**.
- Tap **Apple Account**.
- Tap **Sign In Manually**.
- Enter an email address that matches the federated ABM domain, e.g. `user@your-domain.com`, then tap **Proceed**.
- A hint appears: **Apple account for `<Company Name>`**  tap **Proceed**.
- The Keycloak login page is shown with the username pre-filled.
- After signing in with the correct password, a processing screen displays the user's first and last name.
- After a short delay, enter your device PIN.
- **Settings Apple Account** now shows the connected user with the correct email address.

The ABM user account is now linked to the federated Keycloak user and can be
managed through Apple Business Manager.
