from freezing.web import app
from freezing.web.config import init_logging

def main():
    init_logging(color=True)
    app.run(host="0.0.0.0", debug=True)


if __name__ == "__main__":
    main()
