# -*- coding: utf-8 -*-
from config import db
import re


def slugify(value, separator="-"):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    import unicodedata
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore')
    value = unicode(re.sub('[^\w\s-]', '', value).strip())
    return unicode(re.sub('[\s]+', separator, value))


class Manga(db.Model):
    __tablename__ = 'manga'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(200), unique=True)
    url = db.Column(db.Unicode(200), unique=True)
    chapters = db.relationship('Chapter', backref='manga', lazy='dynamic')

    def __init__(self, name=None, url=None):
        self.name = unicode(slugify(name, separator=' '))
        self.url = url

    def __unicode__(self):
        return self.name


class Chapter(db.Model):
    __tablename__ = 'chapter'
    id = db.Column(db.Integer, primary_key=True)
    manga_id = db.Column(db.Integer, db.ForeignKey('manga.id'))
    name = db.Column(db.Unicode(200), unique=False)
    url = db.Column(db.Unicode(200), unique=True)
    cdn_id = db.Column(db.Integer)
    downloaded = db.Column(db.Boolean, default=False)

    def __init__(self, name, url):
        self.name = unicode(slugify(name, separator=' '))
        self.url = url
        # http://readms.com/r/akame_ga_kill/065/3075/1
        self.cdn_id = url.split('/')[-2]  # get cdc id from url

    def __unicode__(self):
        return self.name


def get_or_create(model, **kwargs):
    """SqlAlchemy implementation of Django's get_or_create.
    """
    session = db.session
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance
