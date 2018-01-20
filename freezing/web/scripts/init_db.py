import os
from alembic import command
from alembic.config import Config

from freezing.model import meta, init_model, create_supplemental_db_objects, drop_supplemental_db_objects

from freezing.web import app
from freezing.web.scripts import BaseCommand


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
        init_model(app.config['SQLALCHEMY_DATABASE_URI'], drop=options.drop)

        # Drop and re-add supplementary objects
        drop_supplemental_db_objects(meta.engine)
        create_supplemental_db_objects(meta.engine)

def main():
    InitDb().run()


if __name__ == '__main__':
    main()