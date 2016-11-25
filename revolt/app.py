#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2016 Adrian Perez <aperez@igalia.com>
#
# Distributed under terms of the GPLv3 license.

from gi.repository import Gtk, Gio
from .statusicon import SysTrayStatusIcon
from .window import MainWindow

APP_ID = "org.perezdecastro.Revolt"
APP_COMMENTS = u"Desktop application for Riot.im"
APP_WEBSITE = u"https://github.com/aperezdc/revolt"
APP_AUTHORS = (u"Adrián Pérez de Castro <aperez@igalia.com>",
               u"Jacobo Aragunde Pérez <jaragunde@igalia.com>",
               u"Carlos López Pérez <clopez@igalia.com>")


def _find_resources_path(program_path):
    from os import environ, path as P
    devel = environ.get("__REVOLT_DEVELOPMENT")
    if devel and devel.strip():
        # Use the directory where the executable is located, most likely
        # a checkout of the Git repository.
        path = P.dirname(P.dirname(program_path))
    else:
        # Use an installed location: binary is in <prefix>/bin/revolt,
        # and resources in <prefix>/share/revolt/*
        path = P.join(P.dirname(P.dirname(program_path)), "share", "revolt")
    return P.abspath(P.join(path, APP_ID + ".gresource"))


class RevoltApp(Gtk.Application):
    def __init__(self, program_path):
        Gio.Resource.load(_find_resources_path(program_path))._register()
        Gtk.Application.__init__(self, application_id=APP_ID,
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.settings = Gio.Settings(schema_id=APP_ID)
        self.riot_url = self.settings.get_string("riot-url")
        self.window = None
        self.statusicon = None
        self.connect("shutdown", self.__on_shutdown)
        self.connect("activate", self.__on_activate)
        self.connect("startup", self.__on_startup)

    def __action(self, name, callback):
        action = Gio.SimpleAction.new(name)
        action.connect("activate", callback)
        self.add_action(action)

    def __on_startup(self, app):
        Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)
        self.statusicon = SysTrayStatusIcon(self, 'disconnected')
        self.__action("quit", lambda *arg: self.quit())
        self.__action("about", self.__on_app_about)
        self.__action("preferences", self.__on_app_preferences)
        self.__action("riot-settings", self.__on__riot_settings)

    def __on_shutdown(self, app):
        if self.window is not None:
            self.window.finish()

    def __on_activate(self, app):
        if self.window is None:
            saved_state_path = self.settings.get_property("path")
            saved_state_path += "saved-state/main-window/"
            saved_state = Gio.Settings(schema_id=APP_ID + ".WindowState",
                                       path=saved_state_path)
            self.window = MainWindow(self, saved_state).load_riot()
        self.show()

    def __on_app_about(self, action, param):
        dialog = Gtk.AboutDialog(transient_for=self.window,
                                 program_name=u"Revolt",
                                 authors=APP_AUTHORS,
                                 logo_icon_name=APP_ID,
                                 license_type=Gtk.License.GPL_3_0,
                                 comments=APP_COMMENTS,
                                 website=APP_WEBSITE)
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.present()

    def __build(self, resource, *names):
        builder = Gtk.Builder.new_from_resource(self.get_resource_base_path() + "/" + resource)
        return (builder.get_object(name) for name in names)

    def __on_app_preferences(self, action, param):
        window, url_entry, zoom_factor, zoom_factor_reset, devtools_toggle = \
                self.__build("gtk/preferences.ui",
                             "settings-window",
                             "riot-url-entry",
                             "zoom-factor",
                             "zoom-factor-reset",
                             "dev-tools-toggle")
        self.settings.bind("zoom-factor", zoom_factor, "value",
                           Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind("enable-developer-tools", devtools_toggle, "active",
                           Gio.SettingsBindFlags.DEFAULT)
        zoom_factor_reset.connect("clicked", lambda button:
                                  self.settings.set_double("zoom-factor", 1.0))
        url_entry.set_text(self.riot_url)

        def on_hide(window):
            new_url = url_entry.get_text()
            if new_url != self.riot_url:
                self.settings.set_string("riot-url", new_url)
                self.riot_url = new_url
                self.window.load_riot()
        window.connect("hide", on_hide)
        window.set_transient_for(self.window)
        window.present()

    def __on__riot_settings(self, action, param):
        self.show()
        self.window.load_settings_page()

    def show(self):
        self.window.show()
        self.window.present()
