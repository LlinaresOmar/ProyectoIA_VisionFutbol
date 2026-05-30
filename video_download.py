import os
from pathlib import Path

from SoccerNet.Downloader import SoccerNetDownloader


LOCAL_DIR = Path("videos/input")
PASSWORD_ENV_VAR = "SOCCERNET_PASSWORD"


def main():
    password = os.environ.get(PASSWORD_ENV_VAR)
    if not password:
        raise RuntimeError(f"Set {PASSWORD_ENV_VAR} before downloading SoccerNet data.")

    downloader = SoccerNetDownloader(LocalDirectory=str(LOCAL_DIR))
    downloader.password = password

    game = "europe_uefa-champions-league/2016-2017/2017-04-18 - 21-45 Real Madrid 4 - 2 Bayern Munich"
    downloader.downloadGame(
        files=[
            "video.ini",
            "Labels-v2.json",
            "Labels-cameras.json",
            "1_224p.mkv",
            "2_224p.mkv",
        ],
        game=game,
    )

    print("Descarga completada.")


if __name__ == "__main__":
    main()
