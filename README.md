# Univention Apple School Manager Connector

An app that allows uploading ZIP compressed CSV files
to the Apple School Manager server
to synchronize UCS@schoool users to Apple.
Those look a lot like OneRoster files, but they're not.

* can be installed on DC master and DC backup
* configuration with UCR variables
* app settings as configuration wizard (to set the UCR variables)
* scripts for daily cronjobs to upload fresh CSV/ZIP files

[Meta bug for initial development](http://forge.univention.org/bugzilla/show_bug.cgi?id=47620)

## Build and upload to the appcenter

Should all happen as a pipeline.
Check the ci/cd configuration if you need to repeat any steps manually.

## Publish App

```bash
cd /var/univention/buildsystem2/mirror/appcenter
copy_from_appcenter.test.sh 5.2 <ASM app component ID> # for example apple-school-manager_20250318153240
sudo update_mirror.sh -v appcenter
```

## Update etc/asm_public_key

You can call generate_asm_host_key.py

## Troubleshooting

The apple school manger upload logs are usually not very helpful.
To get better error message, disconnect the SFTP upload and
got through the apple school manager wizard again.
The wizard will give you better error messages.
