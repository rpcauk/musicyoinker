import click
from mymelody.to_database import MyMelodyDatabase
from mymelody.spotipy_client import create_client
import json
from mymelody.spotify_object import Track, Album, Artist
from collections import OrderedDict


default_dir = "C:\\Users\\rasthmatic\\Music"


@click.group()
def main():
    pass


################################################################################
# Collect                                                                      #
################################################################################
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


################################################################################
# Search                                                                       #
################################################################################
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


################################################################################
# Download                                                                     #
################################################################################
@main.group()
def download():
    """Download resources from Spotify (must already have data locally)"""
    pass


@download.command("track")
@click.argument("ids", nargs=-1)
@click.option("-f", "--force", is_flag=True, default=False)
@click.option("-v", "--validate", is_flag=True, default=False)
def download_track(ids, force, validate):
    for id in ids:
        track = Track(id)
        track.download(force=force, validate=validate)


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
        download
        artist.download(validate=validate)


################################################################################
# Validate                                                                     #
################################################################################
@main.group()
def validate():
    """Download resources from Spotify (must already have data locally)"""
    pass


@validate.command("track")
@click.argument("id")
def validate_track(id):
    track = Track(id)
    track.validate(force=True)


################################################################################
# Add                                                                          #
################################################################################


@main.group()
def add():
    pass


@add.command("track")
@click.argument("id")
@click.option("--title", required=True)
@click.option("--length", required=True)  # TODO: What should I do with length?
@click.option("--date", required=True)
@click.option("--disc-number", required=True)
@click.option("--track-number", required=True)
@click.option("--download-url", required=True)
@click.option("--artwork-url", required=True)
@click.option("--explicit", default=0, required=False)
# @click.option("--hidden", required=False)
@click.option("--album", required=True)
@click.option("--artists", multiple=True, required=True)
def add_track(
    id,
    title,
    length,
    date,
    disc_number,
    track_number,
    download_url,
    artwork_url,
    explicit,
    # hidden=0,
    album,
    artists,
):
    print(explicit)
    values = OrderedDict(
        id=id,
        title=title,
        length=length,
        date=date,
        discnumber=disc_number,
        tracknumber=track_number,
        download_url=download_url,
        artwork_url=artwork_url,
        validated=1,
        explicit=explicit,
        # hidden=hidden,
        album=album,
        artists=artists,
    )
    track = Track(id, data=values)
    print(json.dumps(track.data()))


@add.command("album")
@click.argument("id")
@click.option("--title", required=True)
@click.option("--date", required=True)
@click.option("--total-tracks", required=True)
@click.option("--artwork-url", required=True)
@click.option("--explicit", default=0, required=False)
# @click.option("--hidden", required=False)
@click.option("--artists", multiple=True, required=True)
def add_album(
    id,
    title,
    date,
    total_tracks,
    artwork_url,
    explicit,
    artists,
    # hidden=0,
):
    values = OrderedDict(
        id=id,
        title=title,
        date=date,
        total_tracks=total_tracks,
        artwork_url=artwork_url,
        explicit=explicit,
        artists=artists,
        # hidden=hidden,
    )
    album = Album(id, data=values)
    print(json.dumps(album.data()))


################################################################################
# Get                                                                          #
################################################################################
@main.group()
def get():
    pass


@get.command("track")
@click.argument("id")
def get_track(id):
    track = Track(id)
    print(json.dumps(track.data()))


@get.command("album")
@click.argument("id")
@click.option(
    "--simplify",
    type=click.Choice(["tracks"]),
    multiple=True,
    required=False,
)
def get_album(id, simplify=[]):
    album = Album(id)
    print(json.dumps(album.data(simplify=simplify)))


@get.command("artist")
@click.argument("id")
@click.option(
    "--simplify",
    type=click.Choice(["albums", "tracks"]),
    multiple=True,
    required=False,
)
def get_artist(id, simplify=[]):
    artist = Artist(id)
    print(json.dumps(artist.data(simplify=simplify)))


################################################################################
# Update                                                                       #
################################################################################
@main.group()
def update():
    pass


@update.command("track")
@click.argument("id")
@click.option("--title", required=False)
@click.option("--date", required=False)
@click.option("--disc-number", required=False)
@click.option("--track-number", required=False)
@click.option("--download-url", required=False)
@click.option("--artwork-url", required=False)
@click.option("--explicit", required=False)
@click.option("--hidden", required=False)
@click.option("--album", required=False)
@click.option("--artists", multiple=True, required=False)
def update_track(
    id,
    title,
    date,
    disc_number,
    track_number,
    download_url,
    artwork_url,
    explicit,
    hidden,
    album,
    artists,
):
    values = {
        "title": title,
        "date": date,
        "discnumber": disc_number,
        "tracknumber": track_number,
        "download_url": download_url,
        "artwork_url": artwork_url,
        "explicit": explicit,
        "hidden": hidden,
        "album": album,
        "artists": artists,
    }
    track = Track(id)
    print(json.dumps(track.update(values)))


@update.command("album")
@click.argument("id")
@click.option("--title", required=False)
@click.option("--date", required=False)
@click.option("--total-tracks", required=False)
@click.option("--artwork-url", required=False)
@click.option("--explicit", required=False)
def update_album(id, title, date, total_tracks, artwork_url, explicit):
    values = {
        "title": title,
        "date": date,
        "total_tracks": total_tracks,
        "artwork_url": artwork_url,
        "explicit": explicit,
    }
    album = Album(id)
    print(json.dumps(album.update(values)))


@update.command("album")
@click.argument("id")
@click.option("--name", required=False)
@click.option("--artwork-url", required=False)
def update_album(id, name, artwork_url):
    values = {"name": name, "artwork_url": artwork_url}
    album = Album(id)
    print(json.dumps(album.update(values)))


################################################################################
# Delete                                                                       #
################################################################################
@main.group()
def delete():
    pass


@delete.command("track")
@click.argument("id")
def delete_track(id):
    track = Track(id)
    track.delete()


if __name__ == "__main__":
    main()
