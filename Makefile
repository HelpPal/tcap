# -*- Makefile -*-
# Copyright (c) 2016, TeaCapp LLC
#   All rights reserved.

-include $(buildTop)/share/dws/prefix.mk

APP_NAME      := tcapp
srcDir        ?= $(realpath .)
objDir        ?= $(realpath .)/build
installTop    ?= $(VIRTUAL_ENV)
binDir        ?= $(installTop)/bin
SYSCONFDIR    := $(installTop)/etc
LOCALSTATEDIR := $(installTop)/var
CONFIG_DIR    := $(SYSCONFDIR)/$(APP_NAME)
PYTHON        := $(binDir)/python

DB_FILENAME   := $(shell grep ^DB_NAME $(CONFIG_DIR)/site.conf | cut -f 2 -d '"')
EMAIL_FIXTURE_OPT := $(if $(shell git config user.email),--email="$(shell git config user.email)",)
ASSETS_DIR := $(srcDir)/htdocs/static
#ASSETS_DIR := $(srcDir)/htdocs/bower

# We generate the SECRET_KEY this way so it can be overriden
# in test environments.
SECRET_KEY ?= $(shell $(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@\#$%^*-_=+") for i in range(50)]))' )

DJAODJIN_SECRET_KEY ?= $(shell $(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@\#$%^*-_=+") for i in range(50)]))' )

# Django 1.7,1.8 sync tables without migrations by default while Django 1.9
# requires a --run-syncdb argument.
# Implementation Note: We have to wait for the config files to be installed
# before running the manage.py command (else missing SECRECT_KEY).
RUNSYNCDB     = $(if $(findstring --run-syncdb,$(shell cd $(srcDir) && TCAPP_CONFIG_DIR=$(CONFIG_DIR) $(PYTHON) manage.py migrate --help 2>/dev/null)),--run-syncdb,)


all::
	@echo "Nothing to be done for 'make'."

clean::
	rm -rf $(objDir)/tcapp
	-cd $(srcDir) && rm -rf htdocs/static/.webassets-cache htdocs/static/cache

initdb: install-conf
	-[ -f $(DB_FILENAME) ] && rm -f $(DB_FILENAME)
	cd $(srcDir) && TCAPP_CONFIG_DIR=$(CONFIG_DIR) $(PYTHON) ./manage.py migrate $(RUNSYNCDB) --noinput
	cd $(srcDir) && TCAPP_CONFIG_DIR=$(CONFIG_DIR) $(PYTHON) ./manage.py loadfixtures $(EMAIL_FIXTURE_OPT) tcapp/fixtures/default-db.json
	cd $(srcDir) && TCAPP_CONFIG_DIR=$(CONFIG_DIR) $(PYTHON) ./manage.py import_rent_levels --effective 2017-04-14 --compute-limits tcapp/fixtures/rent-limits.csv
	cd $(srcDir) && TCAPP_CONFIG_DIR=$(CONFIG_DIR) $(PYTHON) ./manage.py import_income_levels --effective 2017-04-14 tcapp/fixtures/income-limits.csv

#	cd $(srcDir) && $(PYTHON) ./manage.py import_projects $(EMAIL_FIXTURE_OPT) tcapp/fixtures/projects-2016-11.csv > saas_organization-2016-11.sql


install:: install-conf

package-theme: build-django-assets
	cd $(srcDir) && install -d htdocs/themes
	cd $(srcDir) && DEBUG=0 $(PYTHON) manage.py package_theme --exclude='.*/' \
		--install_dir=htdocs/themes --build_dir=$(objDir) \
		--include='accounts/' --include='docs/' --include='saas/'
	zip -d $(srcDir)/htdocs/themes/tcapp.zip "tcapp/public/static/cache/angular.js"


build-django-assets: clean
	cd $(srcDir) && DEBUG=1 $(PYTHON) manage.py assets build


# Once tests are completed, run 'coverage report'.
run-coverage: initdb
	cd $(srcDir) && coverage run --source='.' \
		manage.py runserver 8050 --noreload

vendor-assets-prerequisites: $(srcDir)/package.json
	$(installFiles) $^ .
	$(binBuildDir)/npm install --loglevel verbose --cache $(installTop)/.npm --tmp $(installTop)/tmp
	$(installDirs) $(ASSETS_DIR)/fonts $(ASSETS_DIR)/vendor
	$(installFiles) node_modules/jquery/dist/jquery.js $(ASSETS_DIR)/vendor
	$(installFiles) node_modules/font-awesome/css/font-awesome.css $(ASSETS_DIR)/vendor
	$(installFiles) node_modules/font-awesome/fonts/* $(ASSETS_DIR)/fonts
	$(installFiles) node_modules/bootstrap/dist/js/bootstrap.js $(ASSETS_DIR)/vendor
	$(installFiles) node_modules/angular/angular.min.js* $(ASSETS_DIR)/vendor
	$(installFiles) node_modules/angular-ui-bootstrap/dist/ui-bootstrap-tpls.js $(ASSETS_DIR)/vendor
	$(installFiles) node_modules/moment/moment.js $(ASSETS_DIR)/vendor
	$(installFiles) node_modules/dropzone/dist/dropzone.css $(ASSETS_DIR)/vendor
	$(installFiles) node_modules/dropzone/dist/dropzone.js $(ASSETS_DIR)/vendor
	echo ";" >> $(ASSETS_DIR)/vendor/dropzone.js


install-conf:: $(DESTDIR)$(CONFIG_DIR)/credentials \
                $(DESTDIR)$(CONFIG_DIR)/site.conf \
                $(DESTDIR)$(CONFIG_DIR)/gunicorn.conf \
                $(DESTDIR)$(SYSCONFDIR)/sysconfig/$(APP_NAME) \
                $(DESTDIR)$(SYSCONFDIR)/logrotate.d/$(APP_NAME) \
                $(DESTDIR)$(SYSCONFDIR)/monit.d/$(APP_NAME) \
                $(DESTDIR)$(SYSCONFDIR)/systemd/system/$(APP_NAME).service
	install -d $(DESTDIR)$(LOCALSTATEDIR)/db
	install -d $(DESTDIR)$(LOCALSTATEDIR)/run
	install -d $(DESTDIR)$(LOCALSTATEDIR)/log/nginx


# Implementation Note:
# We use [ -f file ] before install here such that we do not blindly erase
# already present configuration files with template ones.
$(DESTDIR)$(SYSCONFDIR)/%/site.conf: $(srcDir)/etc/site.conf
	install -d $(dir $@)
	[ -f $@ ] || \
		sed -e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' \
			-e 's,%(APP_NAME)s,$(APP_NAME),g' \
			-e 's,%(SYSCONFDIR)s,$(SYSCONFDIR),' \
			-e "s,%(ADMIN_EMAIL)s,`cd $(srcDir) && git config user.email`," \
			-e "s,%(DB_NAME)s,$(notdir $(patsubst %/,%,$(dir $@)))," \
			-e "s,%(binDir)s,$(binDir)," \
			-e "s,%(djaodjinSrcDir)s,$(djaodjinSrcDir)," $< > $@

$(DESTDIR)$(SYSCONFDIR)/%/credentials: $(srcDir)/etc/credentials
	install -d $(dir $@)
	[ -f $@ ] || \
		sed -e "s,\%(SECRET_KEY)s,$(SECRET_KEY)," \
			-e "s,\%(DJAODJIN_SECRET_KEY)s,$(DJAODJIN_SECRET_KEY)," \
			$< > $@

$(DESTDIR)$(SYSCONFDIR)/%/gunicorn.conf: $(srcDir)/etc/gunicorn.conf
	install -d $(dir $@)
	[ -f $@ ] || \
		sed -e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' \
			-e 's,%(APP_NAME)s,$(APP_NAME),g' $< > $@

$(DESTDIR)$(SYSCONFDIR)/systemd/system/%.service: \
               $(srcDir)/etc/service.conf
	install -d $(dir $@)
	[ -f $@ ] || sed -e 's,%(srcDir)s,$(srcDir),' \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(binDir)s,$(binDir),' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' \
		-e 's,%(CONFIG_DIR)s,$(CONFIG_DIR),' \
		-e 's,%(SYSCONFDIR)s,$(SYSCONFDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/logrotate.d/%: $(srcDir)/etc/logrotate.conf
	install -d $(dir $@)
	[ -f $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/monit.d/%: $(srcDir)/etc/monit.conf
	install -d $(dir $@)
	[ -f $@ ] || sed \
		-e 's,%(APP_NAME)s,$(APP_NAME),g' \
		-e 's,%(LOCALSTATEDIR)s,$(LOCALSTATEDIR),' $< > $@

$(DESTDIR)$(SYSCONFDIR)/sysconfig/%: $(srcDir)/etc/sysconfig.conf
	install -d $(dir $@)
	[ -f $@ ] || install -p -m 644 $< $@


-include $(buildTop)/share/dws/suffix.mk
