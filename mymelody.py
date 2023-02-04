import click
from mymelody.spotify_download import SpotifyDownload

default_dir = "C:\\Users\\rasthmatic\\Music"


@click.group()
def main():
    pass


@main.command()
@click.argument("id")
def track(id):
    sd = SpotifyDownload("user-library-read")
    sd.track(id, default_dir)
    sd.export_json(f"{id}.json")
    # print(id)


@main.command()
@click.argument("id")
def album(id):
    sd = SpotifyDownload("user-library-read")
    sd.album(id, default_dir)
    # print(id)


@main.command()
@click.argument("id")
def artist(id):
    sd = SpotifyDownload("user-library-read")
    albums = []
    while True:
        results = sd.get_client().artist_albums(
            id, offset=len(albums), album_type="album,single"
        )["items"]
        albums += results
        if len(results) != 20:
            break
    for album in albums:
        sd.album(album["uri"].split(":")[-1], default_dir)
    sd.export_json(f"{id}.json")


if __name__ == "__main__":
    main()
