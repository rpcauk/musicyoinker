import click
from mymelody.to_database import MyMelodyDatabase
from mymelody.spotipy_client import create_client
import json
from mymelody.download import download_track as dt
import os

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
@click.argument("id")
def download_track(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    mmdb.add_track(id)
    dt(mmdb.get_track(id))


@download.command("album")
@click.argument("id")
def download_album(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    mmdb.collect_album(id)
    for track in mmdb.get_album_tracks(id):
        dt(track["track_id"])


@download.command("artist")
@click.argument("id", nargs=-1)
def download_artist(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    for artist_id in id:
        mmdb.collect_artist(artist_id)
        for album in mmdb.get_artist_albums(artist_id):
            mmdb.collect_album(album["album_id"])
            for track in mmdb.get_album_tracks(album["album_id"]):
                dt(track["track_id"])


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
