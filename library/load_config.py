#coding: utf-8
__author__ = 'root'

import os
import ConfigParser


class ConfigFileError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ServerConfig(object):
    config_filename = u'config.cfg'
    getattr_sections = (
        "VIDEO",
        "SERVER",
        "NOTICE",
    )
    _sleep_time = None
    config = None

    def __init__(self, path=""):
        if not path:
            path = os.getcwd()
        self.directory = path
        full_path = os.path.join(self.directory, self.config_filename)

        self.config = ConfigParser.RawConfigParser()
        print full_path
        self.config.read(full_path)
        self._process()


    def _process(self):
        cams = self.config.items('CAMERAS')

        self.cams = []
        for cam in cams:
            name, params = cam
            http, login, password = params.split()

            cam_description = {}
            cam_description['name'] = name
            cam_description['ip'] = http
            cam_description['login'] = login
            cam_description['passwd'] = password

            self.cams.append(cam_description)

        schedule = self.config.items('SCHEDULE')

        self.SCHEDULE = {}
        for record in schedule:
            day, schedule_for_day = record
            self.SCHEDULE[day] = schedule_for_day.split('-')

    def __getattribute__(self, item):
        try:
            attr = object.__getattribute__(self, item)
        except AttributeError:
            for section in self.getattr_sections:
                if self.config.has_option(section, item):
                    attr = self.config.get(section, item)
            # to float as it can
            try:
                attr = float(attr)
                if attr.is_integer():
                    attr = int(attr)
            except ValueError:
                pass

            assert attr, "Do something, you config parser murder me!"
        return attr


    @property
    def RESOLUTION(self):
        width, height = self.config.get('VIDEO', 'RESOLUTION').split()
        return (int(width), int(height))

    @property
    def DIRECTORY(self):
        folder = self.config.get('VIDEO', 'DIRECTORY')
        if not os.path.isabs(folder):
            folder = os.path.join(os.getcwd(), folder)
        return folder

    @property
    def SLEEP_TIME(self):
        if not self._sleep_time:
            self._sleep_time = 1.0/self.FPS
        return self._sleep_time
