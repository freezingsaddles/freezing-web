import logging
import optparse

from colorlog import ColoredFormatter

import abc
from bafs import app
from bafs.exc import CommandError


class BaseCommand(object):
    __metaclass__ = abc.ABCMeta

    # TODO: usage, help, etc.
    @abc.abstractproperty
    def name(self):
        """
        :return: The short name for the command.
        """

    def __init__(self):
        self.logger = None

    def build_parser(self):
        parser = optparse.OptionParser()

        parser.add_option("--debug", action="store_true", dest="debug", default=False,
                          help="Whether to log at debug level.")

        parser.add_option("--quiet", action="store_true", dest="quiet", default=False,
                          help="Whether to suppress non-error log output.")

        parser.add_option("--color", action="store_true", dest="color", default=False,
                          help="Whether to output logs with color.")

        return parser

    def parse(self, args=None):
        parser = self.build_parser()
        return parser.parse_args(args)

    def init_logging(self, options):
        """
        Initialize the logging subsystem and create a logger for this class, using passed in optparse options.

        :param options: Optparse options.
        :return:
        """
        if options.quiet:
            loglevel = logging.ERROR
        elif options.debug:
            loglevel = logging.DEBUG
        else:
            loglevel = logging.INFO

        ch = logging.StreamHandler()
        ch.setLevel(loglevel)

        if options.color:

            formatter = ColoredFormatter(
                    "%(log_color)s%(levelname)-8s%(reset)s [%(name)s] %(message)s",
                    datefmt=None,
                    reset=True,
                    log_colors={
                        'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red',
                    }
            )

        else:
            formatter = logging.Formatter("%(levelname)-8s [%(name)s] %(message)s")

        ch.setFormatter(formatter)

        loggers = [app.logger, logging.getLogger('stravalib'),
                   logging.getLogger('requests'), logging.root]

        for l in loggers:
            if l is app.logger or l is logging.root:
                l.setLevel(logging.DEBUG)
            else:
                l.setLevel(logging.INFO)
            l.addHandler(ch)

        self.logger = logging.getLogger(self.name)

    def run(self, argv=None):
        parser = self.build_parser()
        assert parser is not None, "{}.build_parser() method did not return a parser object.".format(
            self.__class__.__name__)

        (options, args) = parser.parse_args(argv)

        self.init_logging(options)
        try:
            self.execute(options, args)
        except CommandError as ce:
            parser.error(str(ce))
            raise SystemExit(127)

    @abc.abstractmethod
    def execute(self, options, args):
        """
        Perform actual implementation for this command.

        :param options: The options from parsed optparse
        :param args: The args form parsed optparse
        """


