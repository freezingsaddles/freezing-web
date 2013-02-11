import os.path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
#from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('bafs.default_settings')
#app.config.from_pyfile(os.path.join(os.path.dirname(__file__), '..', 'settings.py'), silent=False) # set silent=True for prod?
app.config.from_envvar('BAFS_SETTINGS')

db = SQLAlchemy(app)

from bafs import views # This needs to be after the app is created.