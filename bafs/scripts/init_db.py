import os
from alembic import command
from alembic.config import Config
from bafs import app, db, model
from bafs.scripts import BaseCommand


class InitDb(BaseCommand):
    @property
    def name(self):
        return 'init-db'

    def build_parser(self):
        parser = super(InitDb, self).build_parser()
        parser.add_option("--drop", action="store_true", dest="drop", default=False,
                          help="Whether to drop tables.")
        return parser

    def execute(self, options, args):
        if options.drop:
            app.logger.info("Dropping tables.")
            db.drop_all()
        db.create_all()

        model.rebuild_views()

        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        command.stamp(alembic_cfg, "head")


def main():
    InitDb().run()


if __name__ == '__main__':
    main()