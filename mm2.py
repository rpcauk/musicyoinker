import difflib
import json
import os
import re
import sys
from pathlib import Path

import click
import requests
from dateutil import parser
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3
from spotipy import Spotify, SpotifyOAuth
from spotipy.oauth2 import SpotifyOAuth
from yt_dlp import YoutubeDL
from ytmusicapi import YTMusic

################################################################################
# Spotify Client Creation                                                      #
################################################################################


def _create_client(scope):
    sc_params = {}

    if not scope:
        print(f"No scopes specified!")
        sys.exit(1)
    sc_params["scope"] = scope

    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    if client_id is None:
        print("SPOTIPY_CLIENT_ID environment variable not set")
        sys.exit(1)
    sc_params["client_id"] = client_id

    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    if client_id is None:
        print("SPOTIPY_CLIENT_SECRET environment variable not set")
        sys.exit(1)
    sc_params["client_secret"] = client_secret

    sc_params["redirect_uri"] = os.getenv(
        "SPOTIPY_REDIRECT_URI",
        "https://localhost:8888/callback",
    )

    spotipy_client = Spotify(auth_manager=SpotifyOAuth(**sc_params))
    return spotipy_client


################################################################################
# Metadata                                                                     #
################################################################################


def _get_track_metadata(resp):
    track_data = {}
    track_data["id"] = resp["id"]
    track_data["title"] = resp["name"]
    track_data["date"] = parser.parse(resp["album"]["release_date"]).strftime(
        "%Y-%m-%d"
    )
    track_data["discnumber"] = str(resp["disc_number"])
    track_data["tracknumber"] = str(resp["track_number"])
    track_data["album"] = resp["album"]["name"]
    track_data["album_artists"] = [
        artist["name"] for artist in resp["album"]["artists"]
    ]
    track_data["artists"] = [artist["name"] for artist in resp["artists"]]
    print(track_to_string(track_data))
    track_data["download_url"] = _download_url(resp)
    track_data["artwork_url"] = _artwork_url(resp)
    return track_data


def _download_url(resp):
    ytm = YTMusic()
    artist = resp["artists"][0]["name"]
    album = resp["album"]["name"]
    title = (resp["name"],)
    try:
        yid = ytm.search(f"{artist} {album} {title}", filter="songs")[0]["videoId"]
        url_prefix = "https://music.youtube.com/watch?v="
        url = url_prefix + yid
        print(url)
        new_id = input("New id? ")
        if new_id:
            url = url_prefix + new_id
        return url
    except:
        return None


def _artwork_url(resp):
    album_images = resp["album"]["images"]
    max_image = sorted(album_images, key=lambda i: i["height"], reverse=True)[0]
    return max_image["url"]


################################################################################
# Download                                                                     #
################################################################################


def download_track(track, base_dir):
    if not track["download_url"]:
        print(f"[ERROR  ] No dowload url for {track_to_string(track)}")
        return

    track["artist"] = "; ".join(track["artists"])
    track["albumartist"] = "; ".join(track["album_artists"])

    output_file = track_file(base_dir, track)
    Path(os.path.dirname(output_file)).mkdir(parents=True, exist_ok=True)
    if os.path.exists(output_file):
        # Only enable for logging
        # print(f"[EXISTS ] {track_to_string(track)}")
        return

    # download mp3 file
    ydl_opts = {
        "format": "mp3/bestaudio/best",
        "outtmpl": f"{output_file.split('.')[0]}.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "extractor_retries": 3,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
        ],
    }

    with YoutubeDL(ydl_opts) as ydl:
        error_code = ydl.download(track["download_url"])

    # set mp3 file metadata
    audio = MP3(output_file, ID3=EasyID3)
    exclude_keys = [
        "download_url",
        "artwork_url",
        "artists",
        "album_artists",
        "id",
    ]
    mp3_metadata = {d: v for d, v in track.items() if d not in exclude_keys}
    for attribue, value in mp3_metadata.items():
        audio[attribue] = value
    audio.save()

    # set mp3 artwork (requires different object)
    audio = MP3(output_file, ID3=ID3)
    audio.tags["APIC"] = APIC(
        encoding=0,
        mime="image/jpeg",
        type=3,
        desc="Cover",
        data=requests.get(track["artwork_url"]).content,
    )
    audio.save()


################################################################################
# Utilities                                                                    #
################################################################################


def track_file(base_dir, track):
    s_albumartist = re.sub(r"\W+", "", "".join(track["album_artists"]))
    s_album = re.sub(r"\W+", "", track["album"])
    s_title = re.sub(r"\W+", "", track["title"])
    return f"{base_dir}/{s_albumartist}/{s_album}/{s_title}.mp3"


def track_to_string(track):
    title = track["title"]
    artists = "; ".join(track["artists"])
    album = track["album"]
    return f"{title} by {artists} from {album}"


def collect_track_func(ctx, id):
    track = ctx["tracks"].get(id)
    if track is None:
        track = _get_track_metadata(ctx["client"].track(id))
        ctx["tracks"][id] = track
        print(f"[COLLECT] {track_to_string(track)}")
    else:
        print(f"[EXISTS ] {track_to_string(track)}")


def export_data(ctx):
    data = {"tracks": ctx["tracks"], "playlists": ctx["playlists"]}
    with open(ctx["file"], "w+") as fh:
        fh.write(json.dumps(data, indent=4, sort_keys=True))


################################################################################
# CLI                                                                          #
################################################################################


@click.group()
@click.pass_context
def main(ctx):
    ctx.obj = {}
    ctx.obj["client"] = _create_client(["user-library-read"])
    ctx.obj["base_dir"] = "/home/ryan/music2"
    ctx.obj["file"] = "mm2.json"
    if os.path.isfile(ctx.obj["file"]):
        with open(ctx.obj["file"], "r") as fh:
            data = json.load(fh)
            ctx.obj["tracks"] = data["tracks"]
            ctx.obj["playlists"] = data["playlists"]
    else:
        ctx.obj["tracks"] = {}
        ctx.obj["playlists"] = {}


@main.command()
@click.option(
    "--tracks",
    required=False,
    default="",
    help="Comma separated list of track ids",
)
@click.option(
    "--albums",
    required=False,
    default="",
    help="Comma separated list of album ids",
)
@click.pass_obj
def collect(ctx, tracks, albums):
    if not (tracks or albums):
        print("must specify at least either track, album, or artist")
        sys.exit(1)
    tracks_to_collect = tracks.split(",") if tracks else []
    albums_to_collect = albums.split(",") if albums else []
    for album in albums_to_collect:
        tracks_to_collect += [
            track["id"] for track in ctx["client"].album_tracks(album)["items"]
        ]
    for track in tracks_to_collect:
        collect_track_func(ctx, track)
    export_data(ctx)


@main.command("playlist")
@click.argument("id")
@click.pass_obj
def playlist(ctx, id):
    # Series of track ids (maybe albums/artists) and mark as playlist (only existing)
    data = ctx["client"].playlist(id)
    name = re.sub(r"\W+", "", data["name"])
    playlist_tracks = [track["track"] for track in data["tracks"]["items"]]

    # generate diff
    current_titles = []
    for track in ctx["playlists"].get(id, {"tracks": []})["tracks"]:
        current_titles.append(track_to_string(ctx["tracks"][track]))
    new_titles = []
    for track in playlist_tracks:
        track_simple = {}
        track_simple["title"] = track["name"]
        track_simple["album"] = track["album"]["name"]
        track_simple["artists"] = [
            artist["name"] for artist in track["album"]["artists"]
        ]
        new_titles.append(track_to_string(track_simple))

    if current_titles == new_titles:
        print("no changes to playlist")
        return
    for line in difflib.unified_diff(current_titles, new_titles):
        print(line)

    # Check input if want to proceed?
    proceed = input("Proceed? (y/n) ")
    if proceed.lower() == "n":
        return

    playlist_track_ids = [track["id"] for track in playlist_tracks]
    for track_id in playlist_track_ids:
        collect_track_func(ctx, track_id)
    collected_tracks = [
        track_file("..", ctx["tracks"][track_id]) for track_id in playlist_track_ids
    ]
    ctx["playlists"][id] = {"name": name, "tracks": playlist_track_ids}
    export_data(ctx)
    with open(f"{ctx['base_dir']}/Playlists/{name}.m3u", "w") as fh:
        fh.write("#EXTM3U\n")
        for line in collected_tracks:
            fh.write(f"{line}\n")


@main.command("download")
@click.option("--id", required=False)
@click.pass_obj
def download(ctx, id):
    print("Downloading... ")
    if id:
        data = {k: v for k, v in ctx["tracks"]}
    else:
        data = ctx["tracks"]

    if not data:
        print("track not yet collected!")
        return

    for track in data.values():
        download_track(track, ctx["base_dir"])


if __name__ == "__main__":
    main()
