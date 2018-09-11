#!/bin/bash

set -e
set -x

APP_VERSION="4.3/asm=1.0"
DOCKER_IMAGE="docker.software-univention.de/ucs-appbox-amd64:4.3-0"

selfservice () {
	local uri="https://provider-portal.software-univention.de/appcenter-selfservice/univention-appcenter-control"
	local first=$1
	shift
	curl -sSfL "$uri" | python - "$first" --username=${USER} --pwdfile ~/.selfservicepwd "$@"
}

die () {
	echo "$@"
	exit 0
}


test -n "$(git status -s)" && die "Changes in repo, do not upload app!"

# build package
docker run -v "$(pwd)":/opt --rm $DOCKER_IMAGE /bin/bash -c "
	apt-get -y update;
	apt-get -y install dpkg-dev build-essential debhelper univention-config-dev python-all ucslint-univention python2.7-dev univention-management-console-dev;
	cp -a /opt/apple-school-manager /tmp;
	cd /tmp/apple-school-manager
	dpkg-buildpackage;
	cp /tmp/*.deb /opt
	"

selfservice upload "$APP_VERSION" univention-apple-school-manager-connector*.deb  univention-oneroster-lib*.deb asm.settings configure_host

rm -f univention-*.deb
rm -f ucs-*.deb
