#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import traceback
import shutil
import os
import requests
import bs4
from models import Manga, Chapter
from config import *
import urllib
import logging

from Queue import Queue
from threading import Thread

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - (%(threadName)-10s) - %(levelname)s - %(message)s')
logging.getLogger('requests').setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

s = requests.Session()
a = requests.adapters.HTTPAdapter(max_retries=5)
b = requests.adapters.HTTPAdapter(max_retries=5)
s.mount('http://', a)
s.mount('https://', b)

# create tables sqlalchemy init
def create_tables():
    db.create_all()


# create dir if not exist
def ensure_dir(f):
    try:
        os.makedirs(f)
    except OSError:
        if not os.path.isdir(f):
            raise


# get manga list from mangastream if not in database add
def updateMangaList():
    page = s.get(base_url)
    soup = bs4.BeautifulSoup(page.text, 'lxml', from_encoding="utf-8")
    # a tags in table that have table and table-striped classes
    for a in soup.select('table.table.table-striped a[href^=' + base_url + ']'):
        try:
            # if not in database add
            if db.query(Manga).filter_by(url=unicode(a.attrs.get('href'))).first() is None:
                manga = Manga(unicode(a.string), unicode(a.attrs.get('href')))
                db.add(manga)
                db.session.commit()

        except:
            traceback.print_exc()
    db.session.remove()


# get chapter of given manga
def get_chapter(manga):
    manga = db.query(Manga).filter_by(id=manga).first()
    logger.info('Get chapters of {}'.format(manga.name))
    page = s.get(manga.url)
    soup = bs4.BeautifulSoup(page.text, 'lxml', from_encoding="utf-8")
    # a tags in table that have table and table-striped classes
    for a in soup.select('table.table.table-striped a'):
        try:
            # if not in database add
            if db.query(Chapter).filter_by(url=unicode(a.attrs.get('href')[:-1])).first() is None:
                chapter = Chapter(unicode(a.string), unicode(a.attrs.get('href')[:-1]))
                page = s.get(chapter.url, allow_redirects=False)
                manga.chapters.append(chapter)
        except:
            traceback.print_exc()

    db.session.commit()
    db.session.remove()


# download given chapter
def download_chapter(chapter):
    chapter = db.query(Chapter).filter_by(id=chapter).first()
    logger.info('Download : {}'.format(chapter.name))
    dir = os.path.join(outdir, chapter.manga.name, chapter.name)
    shutil.rmtree(dir, ignore_errors=True)
    if os.path.isdir(dir):
        logger.error('Path not empty: {}'.format(dir))
        return
    page = requests.get(chapter.url, allow_redirects=False)
    if not page.ok:
        logger.error('Chapter deleted from site: {}'.format(chapter.name))
        return
    ensure_dir(dir)
    i = 1
    error = False
    while True:
        page = s.get(chapter.url + unicode(i), allow_redirects=False)
        i += 1
        if page.status_code == 302 or error:
            # zip chapter
            shutil.make_archive(dir, 'zip', dir)
            chapter.downloaded = True
            shutil.rmtree(dir, ignore_errors=True)
            logger.info('Download finished {}'.format(chapter.name))
            break
        soup = bs4.BeautifulSoup(page.text, 'lxml')
        img = soup.select('#manga-page')[0].attrs.get('src')
        r = s.get(img, stream=True)
        if r.status_code == 200:
            with open(os.path.join(dir, img.split("/")[-1]), 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        else:
            logger.error('Download error {}'.format(chapter.name))
            error=True

    db.session.commit()
    db.session.remove()


class DownloadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the work from the queue and expand the tuple
            chapter = self.queue.get()
            download_chapter(chapter)
            self.queue.task_done()


class GetChapterWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            # Get the work from the queue and expand the tuple
            manga = self.queue.get()
            get_chapter(manga)
            self.queue.task_done()


def main():
    ensure_dir(outdir)
    create_tables()
    updateMangaList()
    queue = Queue()
    for x in range(10):
        worker = GetChapterWorker(queue)
        # Setting daemon to True will let the main thread exit even though the workers are blocking
        worker.daemon = True
        worker.start()
    for manga in db.query(Manga).all():
        logger.info('Queueing manga {}'.format(manga.name))
        queue.put(manga.id)
    queue.join()
    queue = Queue()
    for x in range(3):
        worker = DownloadWorker(queue)
        # Setting daemon to True will let the main thread exit even though the workers are blocking
        worker.daemon = True
        worker.start()
    for chapter in db.query(Chapter).filter_by(downloaded=False).all():
        logger.info('Queueing chapter {}'.format(chapter.name))
        queue.put(chapter.id)
    queue.join()


main()
