from flask import Flask
from flask_sqlalchemy import SQLAlchemy
#from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)

# XXX: Add configuration ...
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'

db = SQLAlchemy(app)