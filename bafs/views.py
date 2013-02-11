'''
Created on Feb 10, 2013

@author: hans
'''
from bafs import app

@app.route("/")
def hello():
    return "Hello World!"

