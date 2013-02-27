'''
Created on Feb 10, 2013

@author: hans
'''
import json
import copy
from collections import defaultdict
from datetime import datetime

from flask import render_template, redirect, url_for, current_app, request, Blueprint

from sqlalchemy import text
from dateutil import rrule, parser 

from bafs import app, db
from bafs.utils import gviz_api
from bafs.model import Team

blueprint = Blueprint('general', __name__)

@blueprint.route("/")
def index():
    return render_template('index.html')

@blueprint.route("/leaderboard")
def leaderboard():
    return redirect(url_for('.team_leaderboard'))

@blueprint.route("/leaderboard/team")
def team_leaderboard():
    return render_template('leaderboard/team.html')

@blueprint.route("/leaderboard/team_various")
def team_leaderboard_various():
    return render_template('leaderboard/team_various.html')

@blueprint.route("/leaderboard/individual")
def indiv_leaderboard():
    return render_template('leaderboard/indiv.html')

@blueprint.route("/leaderboard/individual_various")
def indiv_leaderboard_various():
    return render_template('leaderboard/indiv_various.html')

@blueprint.route("/trends")
def trends():
    return redirect(url_for('.team_cumul_trend'))

@blueprint.route("/trends/team_cumul")
def team_cumul_trend():
    return render_template('trends/team_cumul.html')