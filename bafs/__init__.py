import os
import os.path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

#from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('bafs.default_settings')
if 'BAFS_SETTINGS' in os.environ:
    app.config.from_envvar('BAFS_SETTINGS')

app.secret_key = app.config['SESSION_SECRET']
if not app.secret_key:
    raise RuntimeError("Configuraiton error.  No SESSION_SECRET configuration variable defined.")

# Register our blueprints
db = SQLAlchemy(app)

from bafs.views import general, chartdata, people # This needs to be after the app is created.
app.register_blueprint(general.blueprint)
app.register_blueprint(chartdata.blueprint, url_prefix='/chartdata')
app.register_blueprint(people.blueprint, url_prefix='/people')