import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import List
import os
import sys
from utils import track_length
import requests
from yt_dlp import YoutubeDL
from mutagen.id3 import ID3, APIC, COMM
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3


class SpotifyDownload:
    def __init__(
        self,
        scope,
        spotipy_client_id=None,
        spotipy_client_secret=None,
        spotipy_redirect_uri=None,
    ) -> None:
        self._spotipy_client = self._create_spotipy_client(
            scope=scope,
            spotipy_client_id=spotipy_client_id,
            spotipy_client_secret=spotipy_client_secret,
            spotipy_redirect_uri=spotipy_redirect_uri,
        )
        self._config = {"tracks": {}, "artwork": {}}

    def _create_spotipy_client(
        self,
        scope: List[str],
        spotipy_client_id=None,
        spotipy_client_secret=None,
        spotipy_redirect_uri=None,
    ):
        sc_params = {}

        if not scope:
            print(f"No scopes specified, check the link below for possible options")
            print(
                f"https://developer.spotify.com/documentation/general/guides/authorization/scopes/"
            )
            sys.exit(1)
        sc_params["scope"] = scope

        required_values = True
        if not os.getenv("SPOTIPY_CLIENT_ID") and not spotipy_client_id:
            print(f"[SPOTIPY_CLIENT_ID] value not found!")
            print(f"Either set the environment variable")
            print(f"Or override with a parameter value")
            required_values = required_values and False
        elif spotipy_client_id:
            print(f"Overriding [SPOTIPY_CLIENT_ID] value from parameter")
            sc_params["client_id"] = spotipy_client_id
        elif os.getenv("SPOTIPY_CLIENT_ID"):
            print(f"Using [SPOTIPY_CLIENT_ID] from environment variable")
            sc_params["client_id"] = os.getenv("SPOTIPY_CLIENT_ID")
        print()

        if not os.getenv("SPOTIPY_CLIENT_SECRET") and not spotipy_client_id:
            print(f"[SPOTIPY_CLIENT_SECRET] value not found!")
            print(f"Either set the environment variable")
            print(f"Or override with a parameter value")
            required_values = required_values and False
        elif spotipy_client_id:
            print(f"Overriding [SPOTIPY_CLIENT_SECRET] value from parameter")
            sc_params["client_secret"] = spotipy_client_secret
        elif os.getenv("SPOTIPY_CLIENT_SECRET"):
            print(f"Using [SPOTIPY_CLIENT_SECRET] from environment variable")
            sc_params["client_secret"] = os.getenv("SPOTIPY_CLIENT_SECRET")
        print()

        if not required_values:
            sys.exit(1)

        default_redirect = "https://localhost:8888/callback"
        if not os.getenv("SPOTIPY_REDIRECT_URI") and not spotipy_redirect_uri:
            print(f"[SPOTIPY_REDIRECT_URI] value not found!")
            print(f"Either set the environment variable")
            print(f"Or override with a parameter value")
            print(f"Using default value [{default_redirect}]")
            sc_params["redirect_uri"] = default_redirect
        elif spotipy_redirect_uri:
            print(f"Overriding [SPOTIPY_REDIRECT_URI] value from parameter")
            sc_params["redirect_uri"] = spotipy_redirect_uri
        elif os.getenv("SPOTIPY_REDIRECT_URI"):
            print(f"Using [SPOTIPY_REDIRECT_URI] from environment variable")
            sc_params["redirect_uri"] = os.getenv("SPOTIPY_REDIRECT_URI")
        print()

        spotipy_client = spotipy.Spotify(auth_manager=SpotifyOAuth(**sc_params))
        return spotipy_client

    def download_track(self, track_id, output_dir=os.getcwd()):
        resp = self._spotipy_client.track(track_id)
        track_config = {}
        track_config["metadata"] = {
            "title": resp["name"],
            "artist": "; ".join([artist["name"] for artist in resp["artists"]]),
            "album": resp["album"]["name"],
            "albumartist": "; ".join(
                [artist["name"] for artist in resp["album"]["artists"]]
            ),
            "length": track_length(resp["duration_ms"]),
            "date": resp["album"]["release_date"],
            "discnumber": str(resp["disc_number"]),
            "tracknumber": str(resp["track_number"]),
        }

        track_config[
            "file"
        ] = f"{output_dir}\\{''.join(e for e in track_config['metadata']['title'] if e.isalnum())}.mp3"
        track_config["artwork_url"] = sorted(
            resp["album"]["images"], key=lambda i: i["height"], reverse=True
        )[0]["url"]

        print(
            f"{track_config['metadata']['title']} {track_config['artwork_url'] in self._config['artwork']}"
        )

        if track_config["artwork_url"] not in self._config["artwork"]:
            self._config["artwork"][track_config["artwork_url"]] = requests.get(
                track_config["artwork_url"]
            ).content

        with YoutubeDL({"noplaylist": True}) as ydl:
            search_url = (
                "ytsearch1:"
                + f"{track_config['metadata']['artist'].split(';')[0]} "
                + f"{track_config['metadata']['title']} "
                + '"Auto-generated by YouTube"'
            )
            download_url = ydl.extract_info(url=search_url, download=False)["entries"][
                0
            ]["webpage_url"]
            track_config["download_url"] = download_url.replace("www", "m")

        self._config["tracks"][track_id] = track_config

        ydl_opts = {
            "format": "mp3/bestaudio/best",
            "outtmpl": track_config["file"],
            "quiet": True,
            "no_warnings": True,
            "extractor_retries": 3,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
            ],
        }

        with YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download(track_config["download_url"])

        audio = MP3(track_config["file"], ID3=EasyID3)
        for attribue, value in track_config["metadata"].items():
            audio[attribue] = value
        audio.save()

        audio = MP3(track_config["file"], ID3=ID3)
        audio.tags["COMM:DLU:ENG"] = COMM(
            encoding=0,
            lang="ENG",
            desc="download_url",
            text=[track_config["download_url"]],
        )
        audio.tags["COMM:AWU:ENG"] = COMM(
            encoding=0,
            lang="ENG",
            desc="artwork_url",
            text=[track_config["artwork_url"]],
        )
        audio.tags["APIC"] = APIC(
            encoding=0,
            mime="image/jpeg",
            type=3,
            desc="Cover",
            data=self._config["artwork"][track_config["artwork_url"]],
        )
        audio.save()
