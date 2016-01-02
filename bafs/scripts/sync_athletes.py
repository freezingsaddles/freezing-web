from bafs import db, model, data
from bafs.scripts import BaseCommand


class SyncAthletes(BaseCommand):
    """
    Updates the athlete records, and associates with teams.

    (Designed to be run periodically to ensure that things like names and team
    membership are kept in sync w/ Strava.)
    """

    @property
    def name(self):
        return 'sync-athletes'

    def execute(self, options, args):

        sess = db.session

        # We iterate over all of our athletes that have access tokens.  (We can't fetch anything
        # for those that don't.)

        q = sess.query(model.Athlete)
        q = q.filter(model.Athlete.access_token != None)

        for athlete in q.all():
            self.logger.info("Updating athlete: {0}".format(athlete))
            c = data.StravaClientForAthlete(athlete)
            strava_athlete = c.get_athlete()
            try:
                data.register_athlete(strava_athlete, athlete.access_token)
                data.register_athlete_team(strava_athlete, athlete)
            except:
                self.logger.warning("Error registering athlete {0}".format(athlete), exc_info=True)
                # But carry on

        data.disambiguate_athlete_display_names()


def main():
    SyncAthletes().run()


if __name__ == '__main__':
    main()