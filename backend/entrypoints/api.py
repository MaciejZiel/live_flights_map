from __future__ import annotations

from dotenv import load_dotenv

from backend import create_api_app

load_dotenv()

app = create_api_app()


def main() -> None:
    app.run(
        host=app.config["HOST"],
        port=app.config["PORT"],
        debug=app.config["DEBUG"],
    )


if __name__ == "__main__":
    main()
