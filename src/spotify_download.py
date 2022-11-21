import json
import os
import sys
from typing import Dict, List, Optional

import requests
from dateutil import parser
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, COMM, ID3
from mutagen.mp3 import MP3
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from yt_dlp import YoutubeDL

from track import Track, TrackDecoder, TrackEncoder


class SpotifyDownload:
    def __init__(
        self,
        scope: List[str],
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> None:
        self._spotipy_client = self.create_client(
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        self.tracks = set()  # TODO: Not reducing downloads
        self.artwork = set()

    def create_client(
        self,
        scope: List[str],
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ) -> Spotify:
        sc_params = {}

        if not scope:
            print(f"No scopes specified!")
            sys.exit(1)
        sc_params["scope"] = scope

        client_ids = (client_id, os.getenv("SPOTIPY_CLIENT_ID"))
        client_ids = [x for x in client_ids if x is not None]
        if client_ids:
            sc_params["client_id"] = client_ids[0]

        client_secrets = (client_secret, os.getenv("SPOTIPY_CLIENT_SECRET"))
        client_secrets = [x for x in client_secrets if x is not None]
        if client_ids:
            sc_params["client_secret"] = client_secrets[0]

        if not redirect_uri:
            redirect_uri = "https://localhost:8888/callback"
        redirect_uris = (redirect_uri, os.getenv("SPOTIPY_REDIRECT_URI"))
        redirect_uris = [x for x in redirect_uris if x is not None]
        if client_ids:
            sc_params["redirect_uri"] = redirect_uris[0]

        if len(sc_params) != 4:
            print("Environment variables not set!")
            if os.name == "nt":
                print('  $env:SPOTIPY_CLIENT_ID="<value>"')
                print('  $env:SPOTIPY_CLIENT_SECRET="<value>"')
            else:
                print('  export SPOTIPY_CLIENT_ID="<value>"')
                print('  export SPOTIPY_CLIENT_SECRET="<value>"')
            sys.exit(1)

        spotipy_client = Spotify(auth_manager=SpotifyOAuth(**sc_params))
        return spotipy_client

    def get_client(self) -> Spotify:
        return self._spotipy_client

    def track(self, id: str, output_dir: Optional[str] = None) -> None:
        sc = self.get_client()

        if not output_dir:
            output_dir = os.getcwd()

        track = Track(id, output_dir, spotify=sc.track(id))
        self.tracks.add(track)

        artwork = requests.get(track.artwork_url).content
        self.artwork.add(artwork)

        print(
            f"Downloading track {track.metadata['title']} "
            + f"by {track.metadata['artist']} "
            + f"from {track.metadata['album']} "
            + f"[{id}]"
        )

        self.download(track.download_url, track.output_file)
        self.set_metadata(track.metadata, track.output_file)
        self.set_download_url(track.download_url, track.output_file)
        self.set_artwork_url(track.artwork_url, track.output_file)
        self.set_artwork(artwork, track.output_file)

    def album(self, id: str, output_dir: Optional[str] = None) -> None:
        sc = self.get_client()
        name = sc.album(id)["name"]
        total = sc.album_tracks(id, limit=1)["total"]

        if not output_dir:
            output_dir = f"{os.getcwd()}\\{name}"

        outputs = 0
        while outputs < total:
            tracks = sc.album_tracks(id, limit=10, offset=outputs)
            for track in tracks["items"]:
                self.track(track["id"], output_dir=output_dir)
                outputs += 1

    def playlist(self, id: str, output_dir: Optional[str] = None) -> None:
        sc = self.get_client()
        name = sc.playlist(id)["name"]
        total = sc.playlist_items(id, limit=1)["total"]

        if not output_dir:
            output_dir = f"{os.getcwd()}\\{name}"

        outputs = 0
        while outputs < total:
            tracks = sc.playlist_items(id, limit=10, offset=outputs)
            for track in tracks["items"]:
                # print(track)
                self.track(track["track"]["id"], output_dir=output_dir)
                outputs += 1

    def download(self, download_url: str, output_file: str) -> None:
        ydl_opts = {
            "format": "mp3/bestaudio/best",
            "outtmpl": output_file,
            "quiet": True,
            "no_warnings": True,
            "extractor_retries": 3,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
            ],
        }

        with YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download(download_url)

    def set_metadata(self, metadata: Dict[str, str], output_file: str) -> None:
        audio = MP3(output_file, ID3=EasyID3)
        for attribue, value in metadata.items():
            audio[attribue] = value
        audio.save()

    def set_download_url(self, download_url: str, output_file: str) -> None:
        audio = MP3(output_file, ID3=ID3)
        audio.tags["COMM:DLU:ENG"] = COMM(
            encoding=0,
            lang="ENG",
            desc="download_url",
            text=[download_url],
        )
        audio.save()

    def set_artwork_url(self, artwork_url: str, output_file: str) -> None:
        audio = MP3(output_file, ID3=ID3)
        audio.tags["COMM:AWU:ENG"] = COMM(
            encoding=0,
            lang="ENG",
            desc="artwork_url",
            text=[artwork_url],
        )
        audio.save()

    def set_artwork(self, artwork: str, output_file: str) -> None:
        audio = MP3(output_file, ID3=ID3)
        audio.tags["APIC"] = APIC(
            encoding=0,
            mime="image/jpeg",
            type=3,
            desc="Cover",
            data=artwork,
        )
        audio.save()

    def export_json(self, output_file: str) -> None:
        with open(output_file, "w") as of:
            key = lambda x: (
                x.metadata["artist"].split(";")[0],
                parser.parse(x.metadata["date"]),
                x.metadata["album"],
                int(x.metadata["discnumber"]),
                int(x.metadata["tracknumber"]),
            )
            sorted_tracks = list(sorted(self.tracks, key=key))
            json.dump(sorted_tracks, of, cls=TrackEncoder, indent=4)

    def import_json(self, output_file: str) -> None:
        with open(output_file) as of:
            data = json.load(of, cls=TrackDecoder)
        self.tracks = set(data)
        for track in self.tracks:
            artwork = requests.get(track.artwork_url).content
            self.artwork.add(artwork)
