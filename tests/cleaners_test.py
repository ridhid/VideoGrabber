#coding: utf-8

import logging
from library.cleaner import Cleaner
import os

logging.basicConfig(level=logging.DEBUG, filename=u'cleaners test logs.log')

root = os.path.join(os.getcwd(), 'camera')
life_time = 28
min_free_space = 35


def prepare():
    years = range(2012, 2014)
    months = range(4, 7)
    days = range(19,23)
    for year in years:
        for month in months:
            for day in days:
                folder = os.pathpath.join(root, str(year), str(month), str(day))
                os.makedirs(folder)

def circle(lf, mfs):
    cleaner = Cleaner(root=root, life_time=lf, min_free_space=mfs)
    cleaner.clean_old()
    # cleaner.free_up_disk_space()

def run():
    life_time = range(19,20)
    min_free_space = range(30,40)

    for lf in life_time:
        for mfs in min_free_space:
            circle(lf, mfs)
            print 'new round'


# prepare()
# run()
circle(1, 40)