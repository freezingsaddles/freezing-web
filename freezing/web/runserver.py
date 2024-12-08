from freezing.web import app
from freezing.web.config import config, init_logging


def main():
    init_logging(color=True)
    app.run(host=config.BIND_INTERFACE, debug=True)


if __name__ == "__main__":
    main()
