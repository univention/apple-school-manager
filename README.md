# Univention Apple School Manager Connector

An app that uploads ZIP compressed CSV files
to the Apple School Manager server
to synchronize UCS@school users to Apple.
Those look a lot like OneRoster files, but they're not.

The user facing documentation lives in [`doc/docs`](doc/docs)
and covers installation, configuration, the exported data,
the Keycloak identity provider setup and troubleshooting.

[Meta bug for initial development](http://forge.univention.org/bugzilla/show_bug.cgi?id=47620)

## Build the documentation

```bash
make -C doc html
make -C doc latexpdf
make -C doc livehtml-docs
make -C doc spelling
make -C doc linkcheck
```

The targets run the Sphinx toolchain in a container,
so a local Sphinx installation is not required.
The pipeline builds, checks and publishes the same sources,
see `.gitlab-ci/gitlab-ci-docs.yml`.

## Build and upload to the appcenter

Should all happen as a pipeline.
Check the ci/cd configuration if you need to repeat any steps manually.

## Release a new app version

* Create a new tag with the version number you want to release, e.g.: 1.1.0
* Wait for the tag pipeline until it reaches the `do_release` job
* Is everything looking good so far? The next will make the new version public!
* Start the `do_release` job

Add the new version to `doc/docs/changelog.rst`.
The pipeline renders it into the App Center update text,
see `build_changelog_html.py`.

## Update etc/asm_public_key

You can call generate_asm_host_key.py

## Keycloak with SSF support before app version 26.7.1

`doc/docs/identity-provider.rst` documents the supported setup,
which needs the Keycloak app in version 26.7.1 or later.
On an older Keycloak, build an image with the SSF feature yourself:

* go to the keycloak-app repo
* download the keycloak nightly build `keycloak-999.0.0-SNAPSHOT.tar.gz`
* build the container locally:
  `docker buildx build docker/keycloak --build-arg KEYCLOAK_VERSION=999.0.0-SNAPSHOT -t nightly-keycloak --no-cache`
* export the image to an archive: `docker save -o night-image.tar nightly-keycloak:latest`
* copy the archive to the UCS server,
  or download it there:
  `curl http://t04.service-univention.de/nightly-image.tar --output /var/tmp/nightly-image.tar`

On the UCS server:

* import the image: `docker load -i nightly-image.tar`
* in `/var/cache/univention-appcenter/appcenter.software-univention.de/5.0/keycloak_20260226143602.compose`
  (or whatever keycloak version is installed)
  * replace `image*` with `image: "nightly-keycloak:latest"`
  * append to the `command` to enable the SSF feature:
    `--spi-datastore-legacy-allow-migrate-existing-database-to-snapshot=true --feature-ssf enabled --spi-events-listener-jboss-logging-success-level=info --spi-events-listener-jboss-logging-error-level=warn --log-level=info,org.keycloak.ssf:trace`
* run `univention-app reinitialize keycloak`
