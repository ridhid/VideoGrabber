#coding: utf-8

import os
import time
import PIL.Image as pil
from datetime import datetime
from datetime import timedelta
from subprocess import Popen
from cStringIO import StringIO

import cv
import cv2
import gevent
import logging
import requests
from gevent import spawn
from gevent.pool import Group
from requests.auth import HTTPBasicAuth

from library.scheduler import ManagedControl

start = time.time()
now = lambda: time.time() - start

class Notice(object):

    def _get_cmd(self):
        return 'echo "%s" | mail -s "%s" %s' % (self.message, self.subject,
                                                self.email)

    def _send(self):
        cmd = self.get_cmd()
        Popen(cmd, shell=True)

    def __init__(self, msg, email, subject):
        self.msg = msg
        self._send


class Stream(object):
    codec = cv.CV_FOURCC('T','H','E','O')

    @property
    def timestamp(self):
        return datetime.now().strftime(u" %H:%M:%S")

    @property
    def datestamp(self):
        return datetime.now().strftime(u"%Y/%m/%d/")

    @property
    def writer(self):
        if not hasattr(self, '_writer'):
            folder = self._make_folder(self.name)
            filename = "".join((self.name.lower(), self.timestamp, ".ogg"))
            self.path = os.path.join(folder, filename)
            self._writer = cv.CreateVideoWriter(self.path, self.codec,
                                                self.config.FPS, self.config.RESOLUTION)
        return self._writer

    def _make_folder(self, name):
        folder = os.path.join(self.config.DIRECTORY, self.datestamp, name)
        try:
            os.makedirs(folder)
        finally:
            return folder

    def _convert(self, request):
        """
        Скаченная картинка конвертируется в формат opencv
        """
        image = StringIO(request)
        source = pil.open(image).convert("RGB")
        bitmap = cv.CreateImageHeader(source.size, cv.IPL_DEPTH_8U, 3)
        cv.SetData(bitmap, source.tostring())
        cv.CvtColor(bitmap, bitmap, cv.CV_RGB2BGR)
        return bitmap

    def __init__(self, name, config, sign):
        self.name = name
        self.sign = sign
        self.config = config


    def write(self, response):
        def write(self, response):
            with gevent.Timeout(1, False) as timeout:
                frame = self._convert(response)
                cv.WriteFrame(self.writer, frame)
        gevent.spawn(write, self, response)

    def as_picture(self, name):
        filename = "".join([self.path, name, '.jpg'])
        cv.SaveImage(filename, self._frames[name])

    #todo может быть есть более логичный способ закрыть усе?
    def close(self):
        pass


class Camera(object):

    @property
    def stream(self):
        if not hasattr(self, '_stream'):
            self._stream = Stream(self.name, self.config, self.ip)
        return self._stream

    @stream.deleter
    def stream(self):
        if hasattr(self, '_stream'):
            del self._stream

    @property
    def auth(self):
        auth = getattr(self, '_auth', None)
        if not auth:
            self._auth = HTTPBasicAuth(self.login, self.passwd)
        return self._auth

    @property
    def session(self):
        session = getattr(self, '_session', None)
        if not session:
            self._session = requests.session()
        return self._session

    @property
    def idle(self):
        start_idle = getattr(self, 'idle_time', None)
        if start_idle:
            return datetime.now() - start_idle
        return timedelta(0)

    @idle.setter
    def idle(self, timestamp):
        if timestamp:
            setattr(self, 'idle_time', datetime.now())
        else:
            setattr(self, 'idle_time', False)

    def _process(self, request):
        self.last_request = dict(headers=request.headers.items(),
                                 body=request.content)
        return self.last_request['body']

    def _is_inactivity(self, url):
        max_idle = timedelta(seconds=60*self.config.INACTIVITY_TIME)
        if self.idle > max_idle:
            logging.warning('cams %s not working' % self.ip)
            msg = "%s по адресу %s не работает более %s " %\
                  (self.name, self.ip, self.idle.total_seconds())
            #todo провести сюда переменную с email
            # Notice(msg)

    def _connect(self):
        request = None
        try:
            request = self.session.get(self.ip,auth=self.auth)
            self.idle = False
        except:
            self.idle = True
        finally:
            return request

    def __init__(self, desc, config):
        self.ip = desc.get('ip', None)
        self.name = desc.get('name', None)
        self.login = desc.get('login', None)
        self.passwd = desc.get('passwd', None)

        self.config = config

    def grab(self):
        request = self._connect()
        if request:
            picture = self._process(request)
            self.stream.write(picture)

    def stop(self):
        del self.stream


class VideoRecord(ManagedControl):

    _cams = list()

    def __init__(self, config):
        logging.info('init video_record')
        self.config = config
        self.stop()
        self._cams = map(lambda desc: Camera(desc, config), self.config.cams)

    def run(self):
        logging.info('video_run')
        gevent.spawn(self.__event_loop).join()

    @property
    def all(self):
        return self._cams

    @property
    def all_works(self):
        return filter(lambda cam: cam.idle.total_seconds() == 0, self._cams)

    @property
    def get_by_name(self, name):
        return filter(lambda cam: cam.name == name, self.all)

    def __event_loop(self):
        """
        Следит за сообщениями записи
        Перезагружает потоки и запускает их заново
        """
        logging.info('init new event loop')
        group = Group()
        while True:
            if self.is_overload():
                self.record()
                self.__grab_loop(self.all)
            gevent.sleep(1)

    def __grab_loop(self, cams):
        while self.is_record() and not self.is_overload():
            greenleets = [spawn(cam.grab) for cam in cams]
            gevent.joinall(greenleets, timeout=self.config.SLEEP_TIME)
            gevent.sleep(self.config.SLEEP_TIME)
        map(lambda cam: cam.stop(), cams)