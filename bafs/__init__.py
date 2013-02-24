import os
import os.path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
#from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('bafs.default_settings')
if 'BAFS_SETTINGS' in os.environ:
    app.config.from_envvar('BAFS_SETTINGS')

# Register our blueprints
db = SQLAlchemy(app)

from bafs.views import general, chartdata # This needs to be after the app is created.
app.register_blueprint(general.blueprint)
app.register_blueprint(chartdata.blueprint, url_prefix='/chartdata')