import logging

from freezing.web import app
from colorlog import ColoredFormatter

def main():
    # Setup some *fancy* logging :)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = ColoredFormatter(
            "%(log_color)s%(levelname)-8s%(reset)s [%(name)s] %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                    'DEBUG':    'cyan',
                    'INFO':     'green',
                    'WARNING':  'yellow',
                    'ERROR':    'red',
                    'CRITICAL': 'red',
            }
    )

    ch.setFormatter(formatter)

    loggers = [app.logger, logging.getLogger('stravalib'),
               logging.getLogger('requests'), logging.root]

    for l in loggers:
        l.setLevel(logging.DEBUG)
        l.addHandler(ch)

    #app.logger.setLevel(logging.DEBUG)
    #app.logger.debug("debug message")
    #app.logger.info("info message")
    #app.logger.warn("warning message")
    #app.logger.error("error message")

    app.run(host='0.0.0.0', debug=True)

if __name__ == '__main__':
    main()
