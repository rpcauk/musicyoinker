import click
from mymelody.to_database import MyMelodyDatabase
from mymelody.spotipy_client import create_client

default_dir = "C:\\Users\\rasthmatic\\Music"


@click.group()
def main():
    pass


@main.group()
def collect():
    pass


@collect.command("track")
@click.argument("id")
def collect_track(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    mmdb.add_track(id)


@collect.command("artist")
@click.argument("id")
def collect_artist(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    mmdb.collect_artist(id)


@main.group()
def search():
    pass


@search.command("track")
@click.argument("id")
def search_track(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    mmdb.get_track(id)


@main.group()
def download():
    pass


@download.command("artist")
@click.argument("id")
def download_artist(id):
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    print(mmdb.get_artist_tracks(id))


# @download.command("track")
# @click.argument("id")
# def download_track(id):


# @main.command()
# @click.argument("id")
# def track(id):
#     sd = SpotifyDownload("user-library-read")
#     sd.track(id, default_dir)
#     sd.export_json(f"{id}.json")
#     # print(id)


# @main.command()
# @click.argument("id")
# def album(id):
#     sd = SpotifyDownload("user-library-read")
#     sd.album(id, default_dir)
#     # print(id)


# @main.command()
# @click.argument("id")
# def artist(id):
#     sd = SpotifyDownload("user-library-read")
#     albums = []
#     while True:
#         results = sd.get_client().artist_albums(
#             id, offset=len(albums), album_type="album,single"
#         )["items"]
#         albums += results
#         if len(results) != 20:
#             break
#     for album in albums:
#         sd.album(album["uri"].split(":")[-1], default_dir)
#     sd.export_json(f"{id}.json")


if __name__ == "__main__":
    main()
