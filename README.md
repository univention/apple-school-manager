# Univention Apple School Manager Connector

An app that allows uploading OneRoster files (ZIP compressed CSV files) to the Apple School Manager server to synchronize UCS@schoool users to Apple.

* can be installed on DC master and DC backup
* configuration with UCR variables
* app settings as configuration wizard (to set the UCR variables)
* scripts for daily cronjobs to upload fresh OneRoster files

Meta bug for initial development: http://forge.univention.org/bugzilla/show_bug.cgi?id=47620

## Build and upload to the appcenter

Set your appcenter password in "~/.selfservicepwd" 
./update-app.sh
or if your username differs from your appcenter username:
bash -c "USER=juern ./update-app.sh"
