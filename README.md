# Freezing Saddles Web

This is the web component for the Freezing Saddles (aka BikeArlington Freezing Saddles, "BAFS") Strava-based winter cycling competition software.

**NOTE:** This application conists of multiple components that work together (designed to run as Docker containers).

1. [freezing-web](https://github.com/freezingsaddles/freezing-web) - The website for viewing leaderboards
1. [freezing-model](https://github.com/freezingsaddles/freezing-model) - A library of shared database and messaging classes.
1. [freezing-sync](https://github.com/freezingsaddles/freezing-sync) - The component that syncs ride data from Strava.
1. [freezing-nq](https://github.com/freezingsaddles/freezing-nq) - The component that receives webhooks and queues them up for syncing.

## Development setup

### Dependencies

* [Python 3.10+](https://www.python.org/downloads/release/python-3100/)
* [pip](https://pypi.org/project/pip/)
* [Python virtual environments (venv)](https://docs.python.org/3/library/venv.html)
* [MySQL 8.0+](https://dev.mysql.com/doc/relnotes/mysql/8.0/en/)

We recommend that for ease of development and debugging, that you install Python 3.10 and pip directly on your workstation. This is tested to work on macOS Sonoma 14.1.2 (23B92) &amp; Sequoia 15.1.1 (24B91), on multiple Linux distributions, and on Windows 10 or 11. While this will work on Windows, most of the advice below relates to running this on a UNIX-like operating system, such as macOS or Ubuntu. Pull requests to improve cross-platform documentation are welcome.

### Optional Dependencies

We *strongly recommend* that you also install [Docker](https://www.docker.com/) to run the database and other services in containers. This will make it easier to set up the database and other services, and to run the application in a production-like environment.

## Installation

Here are some instructions for setting up a development environment, using Python virtual environments:

(If you are running in Windows, run `env/Scripts/activate` instead of `source env/bin/activate`.)

```bash
shell$ git clone https://github.com/freezingsaddles/freezing-web
shell$ cd freezing-web
shell$ python3 -m venv env
shell$ source env/bin/activate
(env) shell$ pip install -e '.[dev]'
```

We will assume for all subsequent shell examples that you are running in the freezing-web activated virtualenv.  (This is denoted by using the "(env) shell$" prefix before shell commands.) Activate the virtualenv when you open a new shell with `source env/bin/activate`.

At this point, you should have all the dependencies installed.

Next, you need to ensure you have a working MySQL database.

### Quick development setup using Docker

This project has a built-in Docker Compose file that can be used to set up a MySQL database for development, _and_ a test web application. This is the easiest way to get started.

```bash
(env) shell$ docker-compose up -d
```

It will take about 15-30 seconds to start the first time. You can see the logs with the command `docker-compose logs -f`.

When it starts up, you can view the Docker version of the Freezing saddles app at [http://127.0.0.1:8000/](http://127.0.0.1:8000/) - it will have an empty database that has been initialized with the schema.

With this Docker Composed setup, the app does not automatically reload when you make changes to the source code, but you can rebuild and redploy it with this command:

```bash
(env) shell$ docker-compose up -d --build && docker-compose logs -f
```

If you want to stop the containers, you can do so with `docker-compose down`.

It's possible to use both the containerized `freezing-server` application _and_ the local development server at the same time, they use different ports.

### Database setup

This application requires MySQL, for historical reasons. @hozn wrote:

> I know, MySQL is a horrid database, but since I have to host this myself (and my shared hosting provider only supports MySQL), it's what we're doing.

These days, @obscurerichard hosts the production site on AWS, where we have a choice of many more databases, but since it started as MySQL it will probably stay as MySQL unless there's a really good reason to move. Perhaps PostgreSQL and its geospacial integration would be a better choice in the long run. Also, [Amazon Aurora](https://aws.amazon.com/rds/aurora/) is really slick for MySQL-compatible datbase engines, so we are sticking with MySQL for now.

#### Alternative: using the freezing-compose orchestrated MySQL Database

You could _instead_ use the MySQL server defined in [freezing-compose](https://github.com/freezingsaddles/freezing-compose) via `docker-compose-dev` as the MySQL database, but you only need to do that if you are testing out container orchestration in a development environment.

#### Alternative: manual database setup

Install MySQL, version 8.0 or newer. The current production server for [Freezing Saddles](https://freezingsaddles.org/) runs MySQL 8.0.

You should create a database and create a user that can access the database.  Something like this might work in the default case:

```bash
(env) shell$ mysql -uroot -p --host 127.0.0.1
# Enter your MySQL root password
mysql> create database freezing;
mysql> create user freezing@localhost identified by 'REDACTED';
mysql> grant all on freezing.* to freezing@127.0.0.1;
```

### Configuring and running freezing-web for local development

This is designed to work with configuration files that are shell environment files. You can also use environment variables directly when running the server.

There is a sample file (`example.cfg`) that you can reference.  You need to set an environment variable called `APP_SETTINGS` to the path to the file you wish to use when you start `freezing-server`.

Edit the file to change the value of `SECRET_KEY`, and set competition dates. Good date ranges are either the range for a prior year's competition, for testing with an archived database dump, or a 3 month range that includes the current date, for testing in conjunction with fresh data downloaded with [freezing-sync])https://github.com/freezingsaddles/freezing-sync)

This component is designed to run as a container and should be configured with environment variables for:
* `DEBUG`: Whether to display exception stack traces, etc.
* `SECRET_KEY`: Used to cryptographically sign the Flask session cookies.
* `SQLALCHEMY_URL`: The URL to the database.
* `STRAVA_CLIENT_ID`: The ID of the Strava application.
* `STRAVA_CLIENT_SECRET`: Secret key for the app (available from App settings page in Strava)
* `TEAMS`: A comma-separated list of team (Strava club) IDs for the competition. = env('TEAMS', cast=list, subcast=int, default=[])
* `OBSERVER_TEAMS`: Comma-separated list of any teams that are just observing, not playing (they can get their overall stats included, but won't be part of leaderboards)
* `START_DATE`: The beginning of the competition.
* `END_DATE`: The end of the competition.

Changing _all_ these values is not necessary for a basic development setup. However, you should ensure these items are set appropriately:
* The team IDs for the competition, `MAIN_TEAM`, `TEAMS` and any `OBSERVER_TEAMS`, if you are loading an archived database.
* `SQLALCHEMY_URL` database credentials, if you are are using something other than the default Docker Compose setup.
* Strava client API credentials, if you want to test athlete registration and authorization. (You don't have to do this to test user pages, see the [impersonation feature](https://github.com/freezingsaddles/freezing-web/pull/332))
* The start and end dates for the competition.

Here is an example of editing the file and starting the webserver using settings from a new `development.cfg` config file:

```bash
(env) shell$ cp example.cfg development.cfg
(env) shell$ nano development.cfg  # Edit the file to set the SECRET_KEY and other settings
(env) shell$ APP_SETTINGS=development.cfg freezing-server
```

Doing this will start the server on port 5000. You can access the site at [http://localhost:5000/](http://localhost:5000/) and if you make changes to the code and save the file, the server will automatically restart.

### Development setup to work with `freezing-model`

During development, you may find you need to make changes to the database. Because this suite of projects uses SQLAlchemy and Alembic, and multiple projects depend on the model, it is in a [separate git repo](https://github.com/freezingsaddles/freezing-model).

This an easy pattern to use to make changes to the project `freezing-model` that this depends on, without having to push tags to the repository. Let's assume you have activated the `freezing-web` virtual environment per the setup instructions above. Then try this:

```bash
(env) shell$ # Assuming you aleready have a working .venv that is activated for freezing-web
(env) shell$ cd ..
(env) shell$ git clone https://github.com/freezingsaddles/freezing-model
(env) shell$ cd freezing-model
(env) shell$ pip install -e '.[dev]'
(env) shell$ cd -
```

Now freezing-model is symlinked in, so you can make changes and add migrations to it.

To get `freezing-web` to permanently use the `freezing-model` changes you will have to tag the `freezing-model` repository with a new version number (don't forget to update its `pyproject.toml` also) and update the tag in [freezing-web/pyproject.toml](pyproject.toml) to match the tag number. It's ok to make a pull request in `freezing-model` and bump the version after merging `master` into your branch.

### Coding standards

The `freezing-web` code is intended to be [PEP-8](https://www.python.org/dev/peps/pep-0008/) compliant. Code formatting is done with [black](https://black.readthedocs.io/en/stable/), [isort](https://pycqa.github.io/isort/) and [djlint](https://www.djlint.com/) and can be linted with [flake8](http://flake8.pycqa.org/en/latest/). See the [.flake8](.flake8) file and install the test dependencies to get these tools (`pip install -r '.[dev]'`).

To run _all_ the linters and formatters, use the following commands:

```bash
bin/lint.sh
bin/fmt.sh
```

This project also has _optional_ support for [pre-commit](https://pre-commit.org) to run these checks automatically before you commit. To install pre-commit, run `pip install pre-commit` and then `pre-commit install` in the root of the repository.

## Production deployment

See [freezing-compose](https://github.com/freezingsaddles/freezing-compose) for a guide to deploying this in production along
with the related containers.

### Beginning of year procedures

* Ensure that someone creates a new Strava main group. Usually the person running the sign-up process does this. [Search for "Freezing"](https://www.strava.com/clubs/search?utf8=%E2%9C%93&text=freezing&location=&%5Bcountry%5D=&%5Bstate%5D=&%5Bcity%5D=&%5Blat_lng%5D=&sport_type=cycling&club_type=all) and you may be surprised to see it has already been created!
* Get the numeric club ID from the URL of the Strava _Recent Activity_ page for the club.
* Gain access to the production server via SSH
* Ensure you have MySQL client access to the production database, either through SSH port forwarding or by running a MySQL client through docker on the production server, or some other means.
* Make a backup of the database:

```bash
mkdir -p ~/backups
time mysqldump > $HOME/backups/freezing-$(date +'%Y-%m-%d').sql
```

* Make a backup of the `.env` file from `/opt/compose/.env`:

```bash
cd /opt/compose
cp .env $HOME/backups/.env-$(date +'%Y-%m-%d')
```

* Edit the `.env` file for the production server (look in `/opt/compose/.env`) as follows:
  * Update the start and end dates
  * Update the main Strava team id `MAIN_TEAM`
  * Remove all the teams in `TEAMS` and `OBSERVER_TEAMS`
  * Update the competition title `COMPETITION_TITLE` to reflect the new year
  * Revise any comments to reflect the new year

```bash
vim /opt/compose/.env
```

* Delete all the data in the following MySQL tables: (see [freezing/sql/year-start.sql](https://github.com/freezingsaddles/freezing-web/blob/main/freezing/sql/year-start.sql))
  * athletes
  * rides
  * ride_efforts
  * ride_geo
  * ride_photos
  * ride_tracks
  * ride_weather
  * teams
* Insert a new record into the `teams` table matching the MAIN_TEAM id:

    insert into teams values (567288, 'Freezing Saddles 2020', 1);

* Restart the services:

    cd /opt/compose && docker compose up -d

* Once the teams are announced (for the original Freezing Saddles competition, typically at the Happy Hour in early January):
  * Add the team IDs for the competition teams and any observer teams (ringer teams) into the production `.env` file
  * Restart the services:

    cd /opt/compose && docker compose up -d

Athletes will get assigned to their correct teams as soon as they join exactly one of the defined competition teams.

## On dumping and restoring the database

It is convenient to dump and restore the database onto a local development environment, and it may be necessary from time to time to restore a database dump in production.

When restoring the database, you should do so as the MySQL root user, or if you don't have access to the real MySQL root user, as the highest privilege user you have access to. Some systems, such as AWS RDS, do not give full MySQL root access but they _do_ have an administrative user.

It would be a good idea to first drop the database, then recreate it along with the freezing user, before restoring the backup.

You may have to edit the resulting SQL dump to redo the SQL SECURITY DEFINER clauses. The examples below do not have the real production root user name in them, observe the error messages from the production dump restoration to get the user name you will need (or ask @obscurerichard in Slack).

```SQL
/*!50013 DEFINER=`mysql-admin-user`@`%` SQL SECURITY DEFINER */
```

In this case you could edit the SQL dump to fix up the root user expressions:

```bash
# Thanks https://stackoverflow.com/a/23584470/424301
LC_ALL=C sed -i.bak 's/mysql-admin-user/root/g' freezing-2023-11-20.sql
```

Here is a lightly redacted transcript of a MySQL interactive session, run on a local dev environment, demonstrating how to prepare for restoring a dump:

```bash
$ docker run -it --rm --network=host mysql:5.7 mysql --host=127.0.0.1 --port=3306 --user=root --password=REDACTED
mysql: [Warning] Using a password on the command line interface can be insecure.
Welcome to the MySQL monitor.  Commands end with ; or \g.
Your MySQL connection id is 33
Server version: 5.7.44 MySQL Community Server (GPL)

Copyright (c) 2000, 2023, Oracle and/or its affiliates.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> drop database if exists freezing;
Query OK, 33 rows affected (0.29 sec)

mysql> create database freezing;
Query OK, 1 row affected (0.00 sec)

mysql> use freezing;
Database changed

mysql> drop user if exists freezing@localhost;
Query OK, 0 rows affected (0.00 sec)

mysql> create user freezing@localhost identified by 'REDACTED';
Query OK, 0 rows affected (0.00 sec)

mysql>  grant all on freezing.* to freezing@localhost;
Query OK, 0 rows affected, 1 warning (0.00 sec)

mysql> quit
Bye
$ LC_ALL=C sed -i.bak 's/mysql-admin-user/root/g' freezing-2023-11-20.sql
$ time docker run -i --rm --network=host mysql:5.7 mysql --host=127.0.0.1 --port=3306 --user=root --password=REDACTED --database=freezing --default-character-set=utf8mb4 < freezing-2023-11-20.sql
mysql: [Warning] Using a password on the command line interface can be insecure.

real    0m43.612s
user    0m0.510s
sys 0m0.994s
$
```

## Scoring system

The Freezing Saddles scoring system has evolved over the years to encourage every day riding for those particpating. The scoring system heavily weights the early miles of each ride. You get these points for riding outdoors,  no indoor trainer rides count:

• 10 points for each day of 1 mile+
• Additional mileage points as follows: Mile 1=10 points; Mile 2=9 pts; Mile 3=8 pts, etc. Miles 10 and over = 1 pt each.
• There is no weekly point cap or distinction between individual and team points. Ride your hearts out!

### Scoring Cheat Sheet for the Mathematically Challenged

Here is a cumulative list of the points you get for riding up to 20 miles per day:

```plaintext
Miles = Points
1 = 20
2 = 29
3 = 37
4 = 44
5 = 50
6 = 55
7 = 59
8 = 62
9 = 64
10 = 65
11 = 66
12 = 67
13 = 68
14 = 69
15 = 70
16 = 71
17 = 72
18 = 73
19 = 74
20 = 75
```

The scores are rounded to the nearest integer point for display, but the system uses precise floating point calculations of points to determine rank. This can lead to some counterintuitive results at first glance, such as a whole-number points tie with the person in the lead having fewer miles recorded.

In 2024, this happened as of Jan 7 between Paul Wilson and Steve Szibler. Check out this detail

```sql
mysql> select a.name, ds.distance, ds.points, ds.ride_date from daily_scores ds inner join athletes a on (ds.athlete_id = a.id) where a.name  like 'Steve S%' or name like 'Paul Wilson' order by name, ride_date;
+-------------------+--------------------+--------------------+------------+
| name              | distance           | points             | ride_date  |
+-------------------+--------------------+--------------------+------------+
| Paul Wilson       | 30.233999252319336 |  85.23399925231934 | 2024-01-01 |
| Paul Wilson       | 32.055999755859375 |  87.05599975585938 | 2024-01-02 |
| Paul Wilson       | 35.689998626708984 |  90.68999862670898 | 2024-01-03 |
| Paul Wilson       | 33.128000259399414 |  88.12800025939941 | 2024-01-04 |
| Paul Wilson       |  36.27000045776367 |  91.27000045776367 | 2024-01-05 |
| Paul Wilson       |   35.4640007019043 |   90.4640007019043 | 2024-01-06 |
| Paul Wilson       |  40.28300094604492 |  95.28300094604492 | 2024-01-07 |
| Steve Szibler🕊     |  85.37000274658203 | 140.37000274658203 | 2024-01-01 |
| Steve Szibler🕊     |  31.36400079727173 |  86.36400079727173 | 2024-01-02 |
| Steve Szibler🕊     | 21.209999084472656 |  76.20999908447266 | 2024-01-03 |
| Steve Szibler🕊     |  40.33599853515625 |  95.33599853515625 | 2024-01-04 |
| Steve Szibler🕊     | 20.131000638008118 |  75.13100063800812 | 2024-01-05 |
| Steve Szibler🕊     |  40.17300033569336 |  95.17300033569336 | 2024-01-06 |
| Steve Szibler🕊     |  7.122000217437744 | 59.419558734504676 | 2024-01-07 |
+-------------------+--------------------+--------------------+------------+
14 rows in set (0.01 sec)

mysql> select a.name, sum(ds.distance), sum(ds.points) from daily_scores ds inner join athletes a on (ds.athlete_id = a.id) where a.name  like 'Steve S%' or name like 'Paul Wilson' group by name order by sum(ds.points) desc;
+-------------------+-------------------+-------------------+
| name              | sum(ds.distance)  | sum(ds.points)    |
+-------------------+-------------------+-------------------+
| Paul Wilson       |           243.125 |           628.125 |
| Steve Szibler🕊     | 245.7060023546219 | 628.0035608716888 |
+-------------------+-------------------+-------------------+
2 rows in set (0.02 sec)
```

## Legal

This software is a community-driven effort, and as such the contributions are owned by the individual contributors:

* Copyright 2015 Ian Will
* Copyright 2019 Hans Lellelid
* Copyright 2020 Jon Renaut
* Copyright 2020 Merlin Hughes
* Copyright 2020 Richard Bullington-McGuire
* Copyright 2020 Adrian Porter
* Copyright 2020 Joe Tatsuko

This software is licensed under the [Apache 2.0 license](LICENSE), with some marked portions available under compatible licenses (such as the [MIT-licensed `test/wget-spider.sh`].)
