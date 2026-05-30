import argparse
import os
from pathlib import Path

from SoccerNet.Downloader import SoccerNetDownloader


LOCAL_DIR = Path("videos/input")
PASSWORD_ENV_VAR = "SOCCERNET_PASSWORD"
DEFAULT_GAME = "europe_uefa-champions-league/2016-2017/2017-04-18 - 21-45 Real Madrid 4 - 2 Bayern Munich"


def parse_args():
    parser = argparse.ArgumentParser(description="Descarga videos y etiquetas de SoccerNet.")
    parser.add_argument(
        "--local-dir",
        default=str(LOCAL_DIR),
        help="Directorio local donde SoccerNet guardara los datos.",
    )
    parser.add_argument(
        "--game",
        default=DEFAULT_GAME,
        help="Identificador del partido en SoccerNet.",
    )
    parser.add_argument(
        "--quality",
        choices=["224p", "720p"],
        default="224p",
        help="Calidad de video a descargar.",
    )
    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="Descargar solo videos, sin video.ini ni etiquetas.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    password = os.environ.get(PASSWORD_ENV_VAR)
    if not password:
        raise RuntimeError(f"Set {PASSWORD_ENV_VAR} before downloading SoccerNet data.")

    downloader = SoccerNetDownloader(LocalDirectory=args.local_dir)
    downloader.password = password

    files = [
        f"1_{args.quality}.mkv",
        f"2_{args.quality}.mkv",
    ]
    if not args.no_labels:
        files = [
            "video.ini",
            "Labels-v2.json",
            "Labels-cameras.json",
            *files,
        ]

    downloader.downloadGame(
        files=files,
        game=args.game,
    )

    print(f"Descarga completada: {args.game} ({args.quality})")


if __name__ == "__main__":
    main()
