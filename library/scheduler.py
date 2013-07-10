#coding: utf-8
from datetime import datetime
from datetime import timedelta

import gevent
import logging
from gevent.event import AsyncResult

from library.cleaner import Cleaner


class ManagedControl(object):
    """
    Базоваый класс для управляемого расписанием объекта
    """
    # объект синхронизации
    _msg = AsyncResult()

    #команды синхронизации
    RECORD = 'record'
    STOP = 'stop'
    OVERLOAD = 'overload'

    def is_record(self):
        message = self._msg.get()
        if message == self.RECORD or message == self.OVERLOAD:
            return True
        return False

    def is_overload(self):
        message = self._msg.get()
        if message == self.OVERLOAD:
            return True
        return False

    def record(self):
        self._overload_start_time()
        self._msg.set(self.RECORD)
        logging.debug("send signal for start record")

    def overload(self):
        logging.debug("overload and create new file for write video-thread")
        self._overload_start_time
        self._msg.set(self.OVERLOAD)

    def stop(self):
        logging.debug("send signal for stop record")
        self._msg.set(self.STOP)

    def _overload_start_time(self):
        self._start_time = datetime.now()


class Scheduler(object):
    """Планировщик записей.

        - запуск записи с камер
        - остановка
        - проверка соответствия временым рамкам
        - очистка старых данных
    """

    def __init__(self, cams_grab, config):
        """
        cams_grab - управляемый объект, наследник ManagedControl
        """
        self.schedule = config.SCHEDULE
        self.grab = cams_grab
        self.clean_path = config.DIRECTORY
        self.clean_period = config.STORAGE_TIME
        self.min_free = config.FREE_SPACE

        overload_period = config.DURATION
        garbage_period = config.GARBAGE_COLLECTION
        self.overload_period = timedelta(seconds=overload_period*60)
        self.garbage_period = timedelta(seconds=garbage_period*60)
        #init local timer
        self.__start_time = datetime.now()
        self.__cleaning_time = datetime.now()

    def run(self):
        """
        бесконечный цикла проверок расписания
        """
        logging.info('run scheduler')
        while True:
            logging.info("new circle in scheduler loop")
            logging.info(str(self.is_record_time()))
            if self.is_record_time():
                if not self.grab.is_record():
                    logging.info("time for record, but record not start")
                    self.grab.overload()
            elif self.grab.is_record():
                logging.info("time for stop, but record start")
                self.grab.stop()

            # overload videothread
            if self.is_overload_time():
                self.grab.overload()
            # clean old videos
            if self.is_cleaning_time():
                self.clean_old()
            logging.info("sleep")
            gevent.sleep(1)

    def is_record_time(self):
        """
        Проверка всех кортежей расписания на день
        """
        hour = datetime.now().strftime("%H").lower()
        day = datetime.now().strftime("%A").lower()

        start, stop = self.schedule[day]
        if int(hour) in range(int(start), int(stop)):
            return True
        return False

    def is_time(self, old_time, period):
        """
        Прошло ли с old_time время , равное period
        """
        duration = datetime.now() - old_time
        return duration > period

    def is_cleaning_time(self):
        """
        Не пора бы очистить старые записи
        """
        result = self.is_time(self.__cleaning_time, self.garbage_period)
        if result:
            self.__cleaning_time = datetime.now()
        return result

    def is_overload_time(self):
        """
        не пора ли перезагрузить запись и сделать пару новых файлов?
        """
        result = self.is_time(self.__start_time, self.overload_period)
        if result:
            self.__start_time = datetime.now()
        return result

    def clean_old(self):
        cleaner = Cleaner(self.clean_path, self.clean_period, self.min_free)
        cleaner.clean_old()
        cleaner.free_up_disk_space()
