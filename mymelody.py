import click
from mymelody.to_database import MyMelodyDatabase
from mymelody.spotipy_client import create_client
import json
from mymelody.download import download_track as dt
import os
from mymelody.spotify_object import Track, Album, Artist

default_dir = "C:\\Users\\rasthmatic\\Music"


@click.group()
def main():
    pass


@main.group()
def collect():
    """Get data from Spotify for track, album, artist, or playlist"""
    pass


@collect.command("track")
@click.argument("id")
def collect_track(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    mmdb.add_track(id)


@collect.command("album")
@click.argument("id")
def collect_album(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    mmdb.collect_album(id)


@collect.command("artist")
@click.argument("id")
def collect_artist(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    mmdb.collect_artist(id)


@main.group()
def search():
    """Search for resource (must already have data locally)"""
    pass


@search.command("track")
@click.argument("id")
@click.option("-a", "--all", is_flag=True, default=False)
def search_track(id, all):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    if all:
        print(json.dumps(mmdb.get_all_tracks()))
        # return mmdb.get_all_tracks()
    else:
        print(json.dumps(mmdb.get_track(id)))


@search.command("artist")
@click.argument("id")
@click.option("-a", "--all", is_flag=True, default=False)
def search_artist(id, all):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    if all:
        print(json.dumps(mmdb.get_all_tracks()))
        # return mmdb.get_all_tracks()
    else:
        print(json.dumps(mmdb.get_artist_tracks(id)))


@main.group()
def download():
    """Download resources from Spotify (must already have data locally)"""
    pass


@download.command("track")
@click.argument("ids", nargs=-1)
@click.option("-v", "--validate", is_flag=True, default=False)
def download_track(ids, validate):
    for id in ids:
        track = Track(id)
        track.download(validate=validate)


@download.command("album")
@click.argument("ids", nargs=-1)
@click.option("-v", "--validate", is_flag=True, default=False)
def download_album(ids, validate):
    for id in ids:
        album = Album(id)
        album.download(validate=validate)


@download.command("artist")
@click.argument("ids", nargs=-1)
@click.option("-v", "--validate", is_flag=True, default=False)
def download_artist(ids, validate):
    for id in ids:
        artist = Artist(id)
        artist.download(validate=validate)


@main.group()
def validate():
    """Download resources from Spotify (must already have data locally)"""
    pass


@validate.command("track")
@click.argument("id")
def validate_artist(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    track = mmdb.get_track(id)
    print(f"Validating {track['title']}")
    print("http://" + track["download_url"])
    new_download = input("New id? ")
    mmdb.validate_track(id, f"m.youtube.com/watch?v={new_download}")
    # os.remove(f"/home/ryan/music/{track['albumartist']}/{track['album']}")
    # TODO: Delete and redownload if updated


if __name__ == "__main__":
    main()
