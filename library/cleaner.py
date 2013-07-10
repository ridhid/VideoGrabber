#coding: utf-8
import os
import re
import statvfs
import logging
from time import mktime
from shutil import rmtree
from datetime import datetime
from datetime import timedelta


class Cleaner(object):
    """
    Объект для поиска и очистки старых записей.
    Основной интерфейс
        либо clean_old - ориентируется на life_time , если срок пришел - папка удаляется
        либо free_up_disk_space - ориентируется на min_free_space, если места не хватает
        то удаляет папки начиная с самой старой
    """
    cleaner = None

    def __new__(cls, *dt, **mp):
        """
        Реализация паттерна одиночка
        """
        if cls.cleaner is None:
            cls.cleaner = object.__new__(cls, *dt, **mp)
        return cls.cleaner

    def __init__(self, root, life_time, min_free_space):
        """
            root - папка с видео
            life_time - срок хранения видео
            min_free_space - если обнаружится свободного места меньше
            чем этого параметра - начнется чистка
        """
        self._prepare_regexp()

        self.root = root
        self.folders = set()
        self.life_time = life_time
        self.min_free_space = min_free_space

    def clean_old(self):
        self._get_folders(self.root)
        self._remove_old()

    def free_up_disk_space(self):
        """
        Чистит место на диске
        """
        self._folder_for_date()
        while self.available_gb < self.min_free_space:
            if self._sort_folders:
                self._remove_folder(self._sort_folders.pop())
            else:
                logging.warning(u"Здес должно быть предупрждение о том, что место закончилось и нечего чистить.")
                break

    @property
    def available_gb(self):
        """
        Возвращает свободное место на диске,
        где лежит root
        """
        st = os.statvfs(self.root)
        bsize = st[statvfs.F_BSIZE]
        available_block = st[statvfs.F_BAVAIL]

        free_kb = available_block * bsize
        # to GB
        self._free = free_kb / (1024 * 1024 * 1024)

        return self._free

    def _prepare_regexp(self):
        """
        Компилирует основные регэкспы на стадии инициализации
        """
        # паттерн для удаления по дате 
        self._date_pattern = re.compile(
            r""".*/(?P<year>\d{4})
            ($|(/(?P<month>\d{1,2})
            ($|/(?P<day>\d{1,2}))))""",
            re.VERBOSE
        )
        # паттерн для поиска самых старых и освобождения места
        self._full_date_pattern = re.compile(
            r'.*/(?P<year>\d*)/(?P<month>\d*)/(?P<day>\d*)/.*'
        )

    def _get_folders(self, path):
        for dir in os.listdir(path):
            full_path = os.path.join(path, dir)
            if os.path.isdir(full_path):
                self.folders.add(full_path)
                self._get_folders(full_path)

        #избавление от папок вида /год/ или /год/месяц/
        for folder in list(self.folders):
            match = re.match(self._full_date_pattern, folder)
            if not match:
                self.folders.remove(folder)

    def _to_date(self, folder):
        """
        Извлекает из имени папки дату создания видео
        Работает , если путь построен по шаблону типа
        /?P<год>\d/>P<месяц>\d/?P<день>\d
        """
        match = re.match(self._date_pattern, folder)
        return datetime(year=int(match.group('year')),
                        month=int(match.group('month')),
                        day=int(match.group('day')))

    def _remove_old(self):
        """
        сравнивает дату в имени\пути папки с максимальным временм сохранения
        """
        max_life_time = timedelta(days=self.life_time)
        for folder in self.folders:
            creation_date = self._to_date(folder)
            life_time = datetime.now() - creation_date
            if life_time > max_life_time:
                self._remove_folder(folder)

    def _remove_folder(self, folder):
        logging.critical('удаление папки')
        logging.critical(folder)
        rmtree(folder, ignore_errors=False, onerror=None)

    def _folder_for_date(self):
        """
        Строит список папок уровня /год/месяц/день
        и сортиртирует по дате
        """
        def sortByData(folder):
            """
            Необходима для сортировки списка.
            Возвращает время в секундах на основе пути.
            Хорошее основание для сортировки , не ?
            """
            date = self._to_date(folder)
            seconds = mktime(date.timetuple())

            return seconds

        self._get_folders(self.root)
        #не трогает папки /год/ или /месяц/
        self._sort_folders = list(self.folders)

        self._sort_folders.sort(key=sortByData, reverse=True)
