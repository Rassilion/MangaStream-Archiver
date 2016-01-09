#!/usr/bin/env python
# -*- coding: utf-8 -*-
import traceback

import requests
import bs4
from models import Manga, Chapter
from config import *


# create tables sqlalchemy init
def create_tables():
    db.create_all()


# get manga list from mangastream if not in database add
def updateMangaList():
    page = requests.get(base_url)
    soup = bs4.BeautifulSoup(page.text, 'lxml')
    for a in soup.select('table.table.table-striped a[href^=' + base_url + ']'):
        try:
            # if not in database add
            if db.query(Manga).filter_by(name=a.string).first() is None:
                manga = Manga(a.string, a.attrs.get('href'))
                db.add(manga)
                db.session.commit()

        except:
            traceback.print_exc()


# get chapter of given manga
def get_chapter(manga):
    page = requests.get(manga.url)
    soup = bs4.BeautifulSoup(page.text, 'lxml')
    for a in soup.select('table.table.table-striped a'):
        try:
            # if not in database add
            print a.string
            if db.query(Chapter).filter_by(url=a.attrs.get('href')).first() is None:
                chapter = Chapter(a.string, a.attrs.get('href'))
                manga.chapters.append(chapter)
                db.session.commit()

        except:
            traceback.print_exc()


# download given chapter
def download_chapter(chapter):
    pass


create_tables()
updateMangaList()
get_chapter(db.query(Manga).filter_by(name="Akame Ga Kill").first())
