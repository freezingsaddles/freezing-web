from freezing.web import app
from freezing.web.config import config


def main():
    app.run(host=config.BIND_INTERFACE, debug=True)


if __name__ == "__main__":
    main()
