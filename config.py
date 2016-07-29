from sqlalchemy_wrapper import SQLAlchemy
import os

db = SQLAlchemy('sqlite:///manga.db', autoflush=False)
base_url = 'http://mangastream.com/manga'
basedir = os.path.abspath(os.path.dirname(__file__))
outdir = os.path.join(basedir, "out")

# this usefull when database is lost, helps to create new database without downloading old chapters but chapter page count still lost
overwriteChapters = False
