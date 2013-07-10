#coding: utf-8
__author__ = 'ridhid'

import gevent
import logging
from gevent import monkey
import sys
from library.wsgi import WSGIVideoServer
from library.load_config import ServerConfig

if __name__ == "__main__":
    logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                        datefmt="%Y-%m-%d %H:%M:%S",
                        level=logging.INFO,
                        filename=u"video.log")
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        config = ServerConfig(path=config_file)
    else:
        config = ServerConfig()
    server = WSGIVideoServer(config)
