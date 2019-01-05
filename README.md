# Freezing Saddles Web

This is the web component for the Freezing Saddles (aka BikeArlington Freezing Saddles, "BAFS") Strava-based
winter cycling competition software.

**NOTE:** This application conists of multiple components that work together (designed to run as Docker containers).
1. [freezing-web](https://github.com/freezingsaddles/freezing-web) - The website for viewing leaderboards   
1. [freezing-model](https://github.com/freezingsaddles/freezing-model) - A library of shared database and messaging classes.
1. [freezing-sync](https://github.com/freezingsaddles/freezing-sync) - The component that syncs ride data from Strava.
1. [freezing-nq](https://github.com/freezingsaddles/freezing-nq) - The component that receives webhooks and queues them up for syncing.

# Development Setup

## Dependencies

* Python 3.6+ (will not work with python 2.x)
* Pip
* Virtualenv (venv)
* MySQL 5.6+ (Sadly.)

We recommend that for ease of development and debugging, that you install Python 3.6 and pip directly on your workstation. This is tested to work on macOS 13.x (High Sierra), on multiple Linux distributions, and on Windows 10. While this will work on Windows 10, most of the advice below relates to running this on a UNIX-like operating system, such as macOS or Ubuntu. Pull requests to improve cross-platform documentation are welcome.

## Installation

Here are some instructions for setting up a development environment:

(If you are running in Windows, run `env/Scripts/activate` instead of `source env/bin/activate`.)
```bash
# Clone repo
shell$ git clone https://github.com/freezingsaddles/freezing-web.git

# Create and activate a virtual environment for freezing-web
shell$ cd freezing-web
shell$ python3.6 -m venv env
shell$ source env/bin/activate
(env) shell$ pip install -r requirements.txt
(env) shell$ python setup.py develop
```

We will assume for all subsequent shell examples that you are running in the freezing-web activated virtualenv.  (This is denoted by using
the "(env) shell$" prefix before shell commands.)    

### Database Setup

This application requires MySQL.  I know, MySQL is a horrid database, but since I have to host this myself (and my shared hosting
provider only supports MySQL), it's what we're doing.

#### DB Setup using Docker

We have some development support Docker Compose files that can help make database setup simpler, head over to the [freezing-compose](https://github.com/freezingsaddles/freezing-compose) repo for those instructions.

#### Manual DB Setup

Install MySQL, version 5.6 or newer. The current production server for https://freezingsaddles.org/ runs MySQL 5.6.

You should create a database and create a user that can access the database.  Something like this might work in the default case:

```bash
shell$ mysql -uroot
mysql> create database freezing;
mysql> grant all on freezing.* to freezing@localhost;
```

## Configure and Run Server

Configuration files are shell environment files (or you can use environment variables dirctly).

There is a sample file (`example.cfg`) that you can reference.  You need to set an environment variable called
`APP_SETTINGS` to the path to the file you wish to use.

Here is an example of starting the webserver using settings from a new `development.cfg` config file:
```bash
(env) shell$ cp example.cfg development.cfg
# Edit the file
(env) shell$ APP_SETTINGS=development.cfg freezing-server
```

Critical things to set include:
* Database URI
* Strava Client info (ID and secret), if you want to test registration/authorization/login.

```bash
# The SQLALchemy connection URL for your MySQL database.
# NOTE THE CHARSET!
# NOTE: If you are using docker use 127.0.0.1 as the host, NOT localhost
SQLALCHEMY_DATABASE_URI=mysql+pymysql://freezing@localhost/freezing?charset=utf8mb4&binary_prefix=true

# These are issued when you create a Strava application.
# These are really only needed if you want to test app authorization or login features.
STRAVA_CLIENT_ID=xxxx1234
STRAVA_CLIENT_SECRET=5678zzzz
```

### Development setup to work with `freezing-model`

During development, you may find you need to make changes to the database. Because this suite of projects uses SQLAlchemy and Alembic, and multiple projects depend on the model, it is in a [separate git repo](https://github.com/freezingsaddles/freezing-model). 

This an easy pattern to use to make changes to the project `freezing-model` that this depends on, without having to push tags to the repository. Assuming you have the project checked out in a directory called `workspace` below your home directory, try this:

1. `cd ~/workspace/freezing-web`
2. `python3 -m venv env`
3. `source env/bin/activate`
4. `cd ~/workspace/freezing-model`
5. `pip install -r requirements.txt && python setup.py develop`
6. `cd -`
7. `pip install -r requirements.txt && python setup.py develop`

Now freezing-model is symlinked in, so you can make changes and add migrations to it.

To get `freezing-web` to permanently use the `freezing-model` changes you will have to tag the `freezing-model` repository with a new version number (don't forget to update `setup.py` also) and update the tag in [freezing-web/requirements.txt](requirements.txt) to match the tag number. It's ok to make a pull request in `freezing-model` and bump the version after merging `master` into your branch.


## Docker Deployment

See [freezing-compose](https://github.com/freezingsaddles/freezing-compose) for guide to deploying this in production along
with the related containers.

This component is designed to run as a container and should be configured with environment variables for:
- `DEBUG`: Whether to display exception stack traces, etc.
- `SECRET_KEY`: Used to cryptographically sign the Flask session cookies.
- `BEANSTALKD_HOST`: The hostname (probably a container link) to a beanstalkd server.
- `BEANSTALKD_PORT`: The port for beanstalkd server (default 11300)
- `SQLALCHEMY_URL`: The URL to the database.
- `STRAVA_CLIENT_ID`: The ID of the Strava application.
- `STRAVA_CLIENT_SECRET`: Secret key for the app (available from App settings page in Strava)
- `TEAMS`: A comma-separated list of team (Strava club) IDs for the competition. = env('TEAMS', cast=list, subcast=int, default=[])
- `OBSERVER_TEAMS`: Comma-separated list of any teams that are just observing, not playing (they can get their overall stats included, but won't be part of leaderboards)
- `START_DATE`: The beginning of the competition.
- `END_DATE`: The end of the competition.
