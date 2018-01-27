# Freezing Saddles Web

This is the web component for the Freezing Saddles (aka BikeArlington Freezing Saddles, "BAFS") Strava-based
winter cycling competition software.

**NOTE:** This application conists of multiple components that work together (designed to run as Docker containers).
1. [freezing-web](https://github.com/freezingsaddles/freezing-web) - The website for viewing leaderboards   
1. [freezing-model](https://github.com/freezingsaddles/freezing-model) - A library of shared database and messaging classes. 
1. [freezing-sync](https://github.com/freezingsaddles/freezing-sync) - The component that syncs ride data from Strava. 
1. [freezing-nq](https://github.com/freezingsaddles/freezing-nq) - The component that receives webhooks and queues them up for syncing.

## Dependencies

* Python 3.6+ (will not work with python 2.x)
* Pip
* Virtualenv (venv)
* MySQL.  (Sadly.)


## Installation

Here are some instructions for setting up a development environment:

```bash
# Clone repo
shell$ git clone https://github.com/freezingsaddles/freezing-web.git

# Create and activate a virtual environment for freezing-web
shell$ cd freezing-web
shell$ python3.6 -m venv env
shell$ source env/bin/activate
(env) shell$ python setup.py develop 
```

We will assume for all subsequent shell examples that you are running in the bafs activated virtualenv.  (This is denoted by using
the "(env) shell$" prefix before shell commands.)    

### Database Setup

This application requires MySQL.  I know, MySQL is a horrid database, but since I have to host this myself (and my shared hosting
provider only supports MySQL), it's what we're doing.

You should create a database and create a user that can access the database.  Something like this might work in the default case:

```bash
shell$ mysql -uroot
mysql> create database freezing;
mysql> grant all on freezing.* to freezing@localhost;
```

## Basic Usage

### Configuration

Configuration files are shell environment files (or you can use environment variables dirctly).

There is a sample file (`example.env`) that you can reference.  You need to set an environment variable called 
`APP_SETTINGS` to the path to the file you wish to use.

Here is an example of starting the webserver using settings from a new `development.env` config file:
```bash
(env) shell$ cp example.env development.env

(env) shell$ APP_SETTINGS=development.env freezing-server
```

Critical things to set include:
* Database URI
* Strava Client info (ID and secret)

```python

# The SQLALchemy connection URL for your MySQL database.
# NOTE THE CHARSET!
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://freezing@localhost/freezing?charset=utf8mb4&binary_prefix=true'

# These are issued when you create a Strava application.
STRAVA_CLIENT_ID = 'xxxx1234'
STRAVA_CLIENT_SECRET = '5678zzzz'
```

## Deployment

This is designed to be deployed with Docker.  See the `Dockerfile` for details.