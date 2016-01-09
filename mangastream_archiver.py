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
import sys


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
    page = requests.get(base_url)
    soup = bs4.BeautifulSoup(page.text, 'lxml', from_encoding="utf-8")
    # a tags in table that have table and table-striped classes
    for a in soup.select('table.table.table-striped a[href^=' + base_url + ']'):
        try:
            # if not in database add
            if db.query(Manga).filter_by(name=unicode(a.string)).first() is None:
                manga = Manga(unicode(a.string), unicode(a.attrs.get('href')))
                db.add(manga)
                db.session.commit()

        except:
            traceback.print_exc()


# get chapter of given manga
def get_chapter(manga):
    page = requests.get(manga.url)
    soup = bs4.BeautifulSoup(page.text, 'lxml', from_encoding="utf-8")
    # a tags in table that have table and table-striped classes
    for a in soup.select('table.table.table-striped a'):
        try:
            # if not in database add
            if db.query(Chapter).filter_by(url=unicode(a.attrs.get('href')[:-1])).first() is None:
                chapter = Chapter(unicode(a.string), unicode(a.attrs.get('href')[:-1]))
                manga.chapters.append(chapter)
                db.session.commit()

        except:
            traceback.print_exc()


# download given chapter
def download_chapter(chapter):
    print "start " + chapter.name.encode('utf-8')
    dir = os.path.join(outdir, chapter.manga.name, chapter.name)
    if os.path.isdir(dir):
        print "path not empty. already downloaded?"
        return
    page = requests.get(chapter.url, allow_redirects=False)
    if not page.ok:
        print "chapter deleted from site"
        return
    ensure_dir(dir)
    i = 1
    while True:
        page = requests.get(chapter.url + unicode(i), allow_redirects=False)
        i += 1
        if page.status_code == 302:
            # zip chapter
            shutil.make_archive(dir, 'zip', dir)
            chapter.downloaded = True
            shutil.rmtree(dir, ignore_errors=True)
            print "chapter finish"
            break
        soup = bs4.BeautifulSoup(page.text, 'lxml')
        img = soup.select('#manga-page')[0].attrs.get('src')
        urllib.urlretrieve(img, os.path.join(dir, img.split("/")[-1]))


def main():
    for manga in db.query(Manga).all():
        print manga.name.encode('utf-8')
        get_chapter(manga)
        for chapter in manga.chapters:
            if not chapter.downloaded:
                download_chapter(chapter)


ensure_dir(outdir)
print basedir
create_tables()
updateMangaList()

main()
