from typing import Dict
import requests
from dateutil import parser
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from yt_dlp import YoutubeDL
import os
import pathlib


# {
#   "id": "30lpjf8sTRSggQHsyPZYuI",
#   "title": "I Wanna Get Better - Live from Spotify NYC",
#   "artists": [
#     {
#       "id": "2eam0iDomRHGBypaDQLwWI",
#       "name": "Bleachers"
#     }
#   ],
#   "albums": [
#     {
#       "id": "6U8viQmbaebf8BWXZezqVq",
#       "title": "Spotify Sessions",
#       "artists": [
#         {
#           "id": "2eam0iDomRHGBypaDQLwWI",
#           "name": "Bleachers"
#         }
#       ]
#     }
#   ]
# }


def artist_from_data(artists):
    return "; ".join([artist["name"] for artist in artists])


def albumartist_from_data(metadata):
    all_artists = []
    for album in metadata["albums"]:
        all_artists += album["artists"]
    return artist_from_data(all_artists)


def album_from_data(metadata):
    return "; ".join([album["title"] for album in metadata.get("albums")])


def download_track(track_data):
    exclude_keys = [
        "download_url",
        "artwork_url",
        "explicit",
        "validated",
        "hidden",
        "artists",
        "albums",
        "id",
        "length",
    ]

    if not track_data["download_url"]:
        print(f"Skipping {track_data['title']} [No download_url]")
        return

    track_data["album"] = album_from_data(track_data)
    track_data["albumartist"] = albumartist_from_data(track_data)
    track_data["artist"] = artist_from_data(track_data["artists"])

    output_dir = f"/home/ryan/music/{track_data['albumartist']}/{track_data['album']}"
    pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_file_name = track_data["title"]
    file_type = "mp3"
    output_file = f"{output_dir}/{output_file_name}.{file_type}"
    if os.path.exists(output_file):
        print(f"Skipping {track_data['title']} [Already exists]")
        return

    download(track_data["download_url"], f"{output_dir}/{output_file_name}", file_type)
    set_metadata(
        {d: v for d, v in track_data.items() if d not in exclude_keys}, output_file
    )
    set_artwork(requests.get(track_data["artwork_url"]).content, output_file)

    print({d: v for d, v in track_data.items() if d not in exclude_keys})


def download(download_url: str, output_file: str) -> None:
    ydl_opts = {
        "format": "mp3/bestaudio/best",
        "outtmpl": f"{output_file}.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "extractor_retries": 3,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        error_code = ydl.download(download_url)


def set_metadata(metadata: Dict[str, str], output_file: str) -> None:
    audio = MP3(output_file, ID3=EasyID3)
    for attribue, value in metadata.items():
        audio[attribue] = value
    audio.save()


def set_extra_metadata(metadata, output_file):
    EasyID3.RegisterTextKey("comment", "COMM")
    audio = MP3(output_file, ID3=EasyID3)
    audio["comment"] = str(metadata)
    audio.save()


def set_artwork(artwork_url: str, output_file: str) -> None:
    audio = MP3(output_file, ID3=ID3)
    audio.tags["APIC"] = APIC(
        encoding=0,
        mime="image/jpeg",
        type=3,
        desc="Cover",
        data=requests.get(artwork_url).content,
    )
    audio.save()
