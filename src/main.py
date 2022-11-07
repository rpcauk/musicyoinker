import click
from spotify_download import SpotifyDownload


@click.group()
def main():
    # print(f"hello {count}")
    print("test")


@main.command()
@click.argument("id")
def track(id):
    sd = SpotifyDownload("user-library-read")
    print(id)


if __name__ == "__main__":
    main()
