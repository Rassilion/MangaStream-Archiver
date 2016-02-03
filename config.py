from sqlalchemy_wrapper import SQLAlchemy
import os

db = SQLAlchemy('sqlite:///manga.db', autoflush=False)
base_url = 'http://mangastream.com/manga'
basedir = os.path.abspath(os.path.dirname(__file__))
outdir = os.path.join(basedir, "out")
