#!/usr/bin/bash

univention-appcenter-control upload \
	--username=jahlers \
	--pwdfile="$HOME"/pw.secret \
	5.0/apple-school-manager=3.1.0 \
	README_UPDATE_DE \
	README_UPDATE_EN
	# asm.settings \
	# configure_host \
	# README_DE \
	# README_EN \
	# README_INSTALL_DE \
	# README_INSTALL_EN \
	# README_POST_INSTALL_DE \
	# README_POST_INSTALL_EN \
