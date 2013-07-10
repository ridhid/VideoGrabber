#coding: utf-8
from gevent import monkey

monkey.patch_all()

from exceptions import NameError
import re
import gevent
from gevent import spawn
from gevent import wsgi
from library.video import VideoRecord
from library.scheduler import Scheduler


class CommonMixin(object):

    def status(self, cam_ctrl):
        response = [cam.name + "\n" for cam in cam_ctrl.all_works]
        return response, "", "200 OK"

    def idle(self, cam_ctrl):
        response = map(lambda cam: "%s %s \n" % (cam.name, cam.idle.total_seconds()),
                       cam_ctrl.all)
        return response, "" , "200 OK"


class Cmd(CommonMixin):
    cmd = r"^/(.*)$"

    def perform(self, uri, *args, **kwargs):
        cmd = self._filter(self.cmd, uri)
        if cmd.isdigit():
            return self.picture_by_numb(cmd, *args, **kwargs)
        return getattr(self, cmd, self.error)(*args, **kwargs)

    def _filter(self, pattern, value):
        return re.match(pattern, value).group(1)

    def error(self, *args, **kwargs):
        return "Unknow command" , "", "200 OK"

    def picture_by_numb(self, number, cam_ctrl):
        if not isinstance(number, int):
            number = int(number)
        response = cam_ctrl.all_works[number].last_request
        return response['body'], response['headers'], "200 OK"

class WSGIVideoServer(object):
    """
    Управление записью по расписанию.
    WSGI сервер , отдающий текущий кадр
    """
    def __init__(self, config):
        self.config = config
        self._cams = VideoRecord(self.config)
        self._scheduler = Scheduler(self._cams, self.config)
        ip = self.config.SERVER_IP
        port = self.config.SERVER_PORT
        self._server = wsgi.WSGIServer((ip, port), self.__video_streaming)
        # run main process: scheduler, video record event loop, socket handler
        jobs = [
            spawn(self._server.serve_forever),
            spawn(self._scheduler.run),
            spawn(self._cams.run),
        ]
        gevent.joinall(jobs)

    def __video_streaming(self, environ, start_response):
        body, headers, status = Cmd().perform(environ['REQUEST_URI'], cam_ctrl=self._cams)
        print start_response
        start_response(status, headers)
        return body

