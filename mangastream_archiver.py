#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import traceback
import shutil
import os
import requests
import bs4
import time
from sqlalchemy.exc import OperationalError

from models import Manga, Chapter
from config import *
import urllib
import logging

from Queue import Queue
from threading import Thread

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - (%(threadName)-10s) - %(levelname)s - %(message)s')
logging.getLogger('requests').setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)


# create dir if not exist
def ensure_dir(f):
    try:
        os.makedirs(f)
    except OSError:
        if not os.path.isdir(f):
            raise


class MangaStreamArchiver:
    s = requests.Session()
    a = requests.adapters.HTTPAdapter(max_retries=5)
    b = requests.adapters.HTTPAdapter(max_retries=5)
    s.mount('http://', a)
    s.mount('https://', b)

    download_error = False

    # get manga list from mangastream if not in database add
    def updateMangaList(self):
        page = self.s.get(base_url)
        soup = bs4.BeautifulSoup(page.text, 'lxml', from_encoding="utf-8")
        # a tags in table that have table and table-striped classes
        for a in soup.select('table.table.table-striped a[href^=' + base_url + ']'):
            # if not in database add
            if db.query(Manga).filter_by(url=unicode(a.attrs.get('href'))).first() is None:
                manga = Manga(unicode(a.string), unicode(a.attrs.get('href')))
                db.add(manga)
                db.session.commit()
        db.session.remove()

    # get chapter of given manga
    def get_chapter(self, manga):
        manga = db.query(Manga).filter_by(id=manga).first()
        logger.info('Get chapters of {}'.format(manga.name))
        page = self.s.get(manga.url)
        if page.status_code == 200:
            soup = bs4.BeautifulSoup(page.text, 'lxml', from_encoding="utf-8")
            # a tags in table that have table and table-striped classes
            for a in soup.select('table.table.table-striped a'):
                # if not in database add
                if db.query(Chapter).filter_by(url=unicode(a.attrs.get('href')[:-1])).first() is None:
                    chapter = Chapter(unicode(a.string), unicode(a.attrs.get('href')[:-1]))
                    manga.chapters.append(chapter)
        else:
            logger.error('manga url error  {}'.format(manga.name))

        # wait for sqllite lock
        while True:
            try:
                db.session.commit()
                break
            except OperationalError:
                pass
        db.session.remove()

    # download given chapter
    def download_chapter(self, chapter, queue):
        start_time = time.time()
        logger.info('Download : {} -- {}'.format(chapter.name, chapter.manga.name))
        # prepare dir
        dir = os.path.join(outdir, chapter.manga.name, chapter.name)
        shutil.rmtree(dir, ignore_errors=True)
        if os.path.isdir(dir):
            logger.error('Path not empty: {}'.format(dir))
            return
        # get page
        page = self.s.get(chapter.url, allow_redirects=False)
        if not page.status_code == 200:
            logger.error('Chapter deleted from site: {}'.format(chapter.name))
            return
        ensure_dir(dir)

        # start download
        url = chapter.url
        i = 1
        img_urls = []
        while True:
            page = self.s.get(url, allow_redirects=False)
            if page.status_code != 200:
                break
            soup = bs4.BeautifulSoup(page.text, 'lxml')
            # select next page
            next_url = soup.select('.next a')
            if not next_url:
                logger.critical('page dropdown selector error')
            url = next_url[0].attrs.get('href')
            # select image url
            img = soup.select('#manga-page')[0].attrs.get('src')

            img_urls.append(img)

            # check chapter end
            page_number = url.split('/')[-1]
            if page_number == 'end' or page_number == '1':  # check for '1' because if next chapter avaible next buton links it

                break
            i += 1
        i = 1
        for img in img_urls:
            queue.put((dir, img, i))
            i += 1

        queue.join()
        # zip chapter
        if not self.download_error:
            shutil.make_archive(dir, 'zip', dir)
            chapter.downloaded = True
            chapter.page = i - 1
            logger.info('Download finished {} time {}'.format(chapter.name, time.time() - start_time))
        else:
            self.download_error = False
            logger.error('Download error {}'.format(chapter.name))

        shutil.rmtree(dir, ignore_errors=True)
        db.session.commit()

    def download_img(self, dir, img, i):
        # get image
        r = self.s.get(img, stream=True)
        # save image to disk
        if r.status_code == 200:
            with open(os.path.join(dir, str(i).zfill(3) + '.' + img.split(".")[-1]), 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        else:
            logger.error('Download error {}'.format(img))
            self.download_error = False

    def run(self):
        ensure_dir(outdir)
        db.create_all()
        self.updateMangaList()
        queue = Queue()
        chapter_workers = []
        for x in range(10):
            worker = GetChapterWorker(queue, self)
            # Setting daemon to True will let the main thread exit even though the workers are blocking
            worker.daemon = True
            chapter_workers.append(worker)
            worker.start()
        for manga in db.query(Manga).all():
            logger.info('Queueing manga {}'.format(manga.name))
            queue.put(manga.id)
        queue.join()
        for w in chapter_workers:
            w.keepRunning = False

        queue2 = Queue()
        for x in range(3):
            worker = DownloadWorker(queue2, self)
            # Setting daemon to True will let the main thread exit even though the workers are blocking
            worker.daemon = True
            worker.start()
        for chapter in db.query(Chapter).filter_by(downloaded=False).all():
            self.download_chapter(chapter, queue2)


class DownloadWorker(Thread):
    def __init__(self, queue, msa):
        Thread.__init__(self)
        self.keepRunning = True
        self.queue = queue
        self.msa = msa

    def run(self):
        while self.keepRunning:
            # Get the work from the queue and expand the tuple
            (dir, img, i) = self.queue.get()
            self.msa.download_img(dir, img, i)
            self.queue.task_done()


class GetChapterWorker(Thread):
    def __init__(self, queue, msa):
        Thread.__init__(self)
        self.keepRunning = True
        self.queue = queue
        self.msa = msa

    def run(self):
        while self.keepRunning:
            # Get the work from the queue and expand the tuple
            manga = self.queue.get()
            self.msa.get_chapter(manga)
            self.queue.task_done()


if __name__ == '__main__':
    MangaStreamArchiver().run()
