import json
import os
import click
import pathlib
from librespot.metadata import TrackId
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.core import Session
from spotipy import Spotify, SpotifyOAuth
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from mutagen.mp3 import MP3
import requests
import tempfile
import pydub
from tqdm import tqdm
import time

################################################################################
# Main class containing config, credentials, and sessions                      #
################################################################################

class MyMelody:
    CLIENT = None
    SESSION = None
    CREDENTIALS = None
    CONFIG = None
    DATA = None

    def __init__(self):
        MyMelody.get_credentials_path()
        MyMelody.create_session()
        MyMelody.create_client()
        MyMelody.load_config()
        MyMelody.load_data()

    # Spotify sessions
    @classmethod
    def get_credentials_path(cls, path="credentials.json"):
        cls.CREDENTIALS = path

    @classmethod
    def create_session(cls):
        conf = Session.Configuration.Builder().set_store_credentials(False).build()
        cls.SESSION = Session.Builder(conf).stored_file(cls.CREDENTIALS).create()

    @classmethod
    def create_client(cls):
        with open(cls.CREDENTIALS, "r") as fh:
            cred_data = json.load(fh)
        params = {k: cred_data[k] for k in ("client_id", "client_secret", "redirect_uri", "scope")}
        cls.CLIENT = Spotify(auth_manager=SpotifyOAuth(**params))

    @classmethod
    def get_content_stream(cls, content_id):
        return cls.SESSION.content_feeder().load(content_id, VorbisOnlyAudioQuality(AudioQuality.HIGH), False, None)
    
    @classmethod
    def get_content_metadata(cls, content_type, content_id, args={}):
        return getattr(cls.CLIENT, content_type)(content_id, **args)

    # Config
    @classmethod
    def load_config(cls, path="config.json"):
        with open(path, "r") as fh:
            cls.CONFIG = json.load(fh)

    @classmethod
    def get_data_path(cls):
        return cls.CONFIG.get("data_path")

    @classmethod
    def get_track_path(cls):
        return cls.CONFIG.get("track_path")

    # Data manipulation
    @classmethod
    def load_data(cls):
        if os.path.exists(MyMelody.get_data_path()):
            with open(MyMelody.get_data_path(), "r") as fh:
                cls.DATA = json.load(fh)
        else:
            cls.DATA = {"playlists": {}, "artists": {}, "tracks": {}}

    @classmethod
    def update_data(cls, content_type, content_id, content_data):
        cls.DATA[content_type][content_id] = content_data

    @classmethod
    def get_data(cls, content_type, content_id=None):
        content = cls.DATA[content_type]
        if content_id:
            content = content.get(content_id)
        return content

    @classmethod
    def write_data(cls):
        with open(MyMelody.get_data_path(), "w") as fh:
            fh.write(json.dumps(cls.DATA, indent=4))


################################################################################
# Utilities                                                                    #
################################################################################

def sanitize_name(name):
    SANITIZE_CHARS = ["\\", "/", ":", "*", "?", "'", "<", ">", '"', "|"]
    for char in SANITIZE_CHARS:
        name = name.replace(char, "_")
    return name


def antiban_wait(seconds=5):
    for i in range(seconds)[::-1]:
        print(f"\rSleep for {i + 1} second(s)...", end="")
        time.sleep(1)
    print()


################################################################################
# Metadata                                                                     #
################################################################################

def get_artist_metadata(artist_id):
    existing_data = MyMelody.get_data("artists", artist_id)
    if existing_data:
        return existing_data

    resp = MyMelody.get_content_metadata("artist", artist_id)
    artist_data = {}
    artist_data["name"] = resp["name"]
    artist_data["artwork_url"] = sorted(resp["images"], key=lambda i: i["height"], reverse=True)[0]["url"]
    artist_data["follow"] = True

    MyMelody.update_data("artists", artist_id, artist_data)
    return artist_data


def get_track_metadata(track_id):
    existing_data = MyMelody.get_data("tracks", track_id)
    if existing_data:
        return existing_data

    resp = MyMelody.get_content_metadata("track", track_id)
    track_data = {}
    track_data["name"] = resp["name"]

    match resp["album"]["release_date_precision"]:
        case "day":
            track_data["release_date"] = resp["album"]["release_date"]
        case "month":
            track_data["release_date"] = resp["album"]["release_date"] + "-01"
        case "year":
            track_data["release_date"] = resp["album"]["release_date"] + "-01-01"

    track_data["disc_number"] = str(resp["disc_number"])
    track_data["track_number"] = str(resp["track_number"])
    track_data["album"] = {
        "id": resp["album"]["id"],
        "name": resp["album"]["name"],
        "artists": {x["id"]: {k:v for k,v in x.items() if k in ("name")} for x in resp["album"]["artists"]}
    }
    track_data["artists"] = {x["id"]: {k:v for k,v in x.items() if k in ("name")} for x in resp["artists"]}
    track_data["artwork_url"] = sorted(resp["album"]["images"], key=lambda i: i["height"], reverse=True)[0]["url"]
    track_data["ignore"] = False

    MyMelody.update_data("tracks", track_id, track_data)
    return track_data


def get_track_description(track_id):
    track_data = get_track_metadata(track_id)
    return track_data["name"] + " - " + "; ".join([x["name"] for x in track_data["artists"].values()])


def get_track_path(track_id):
    track_data = get_track_metadata(track_id)
    track_path = MyMelody.get_track_path()
    for k,v in track_data['album']['artists'].items():
        track_path += f"/{sanitize_name(v['name'])} [{k}]"
    track_path += f"/{sanitize_name(track_data['album']['name'])} [{track_data['album']['id']}]"
    track_path += f"/{sanitize_name(track_data['name'])} [{track_id}].mp3"
    return track_path


################################################################################
# Download                                                                     #
################################################################################

def set_track_tags(track_id):
    track_data = get_track_metadata(track_id)
    track_path = get_track_path(track_id)

    track = MP3(track_path, ID3=EasyID3)
    track["album"] = track_data["album"]["name"]
    track["albumartist"] = "; ".join([x["name"] for x in track_data["album"]["artists"].values()])
    track["artist"] = "; ".join([x["name"] for x in track_data["artists"].values()])
    track["discnumber"] = track_data["disc_number"]
    track["tracknumber"] = track_data["track_number"]
    track["title"] = track_data["name"]
    track["date"] = track_data["release_date"]
    track.save()
    track = MP3(track_path, ID3=ID3)
    track.tags["APIC"] = APIC(
        encoding=0,
        mime="image/jpeg",
        type=3,
        desc="Cover",
        data=requests.get(track_data["artwork_url"]).content,
    )
    track.save()


def download_track(track_id):
    track_data = get_track_metadata(track_id)
    track_path = get_track_path(track_id)

    if track_data["ignore"] or os.path.exists(track_path):
        print(f"Skipping {get_track_description(track_id)}")
        return False

    pathlib.Path(os.path.dirname(track_path)).mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile() as fh:
        stream = MyMelody.get_content_stream(TrackId.from_uri(f"spotify:track:{track_id}"))
        total_size = stream.input_stream.size
        progress = tqdm(total=total_size, desc=get_track_description(track_id))
        downloaded = 0
        fail_count = 0
        while downloaded < total_size:
            remaining = total_size - downloaded
            read_size = min(20000, remaining)

            try:
                data = stream.input_stream.stream().read(read_size)
            except IndexError as e:
                print(f"Stream download failed with id: {track_id}")
                return None

            if not data:
                fail_count += 1
                if fail_count > 10: # Config var
                    break
            else:
                fail_count = 0  # reset fail_count on successful data read

            fh.write(data)
            downloaded += len(data)
            progress.update(len(data))
        progress.close()
        pydub.AudioSegment.from_ogg(fh.name).export(track_path, format="mp3", bitrate="160k")

    set_track_tags(track_id)
    return True


def download_tracks_safely(track_ids):
    num_tracks = 5
    downloaded = 0
    for i in range(len(track_ids)):
        if downloaded != 0 and downloaded % num_tracks == 0:
            antiban_wait()
        download_resp = download_track(track_ids[i])
        if download_resp:
            downloaded += 1


def cleanup_tracks():
    tracks = [k for k,v in MyMelody.get_data("tracks").items() if v["ignore"]]
    if tracks:
        print("Deleting tracks:")
        for track_id in tracks:
            track_path = get_track_path(track_id)
            if os.path.exists(track_path):
                os.remove(track_path)
                print("  " + track_path)
    else:
        print("No tracks to delete")

    deleted = set()
    for current_dir, subdirs, files in os.walk(MyMelody.get_track_path(), topdown=False):
        still_has_subdirs = False
        for subdir in subdirs:
            if os.path.join(current_dir, subdir) not in deleted:
                still_has_subdirs = True
                break
    
        if not any(files) and not still_has_subdirs:
            deleted.add(current_dir)

    if deleted:
        print("Deleting directories:")
        for directory in deleted:
            os.rmdir(directory)
            print("  " + directory)
    else:
        print("No directories to delete")


################################################################################
# Process                                                                      #
################################################################################

def process_tracks(track_ids):
    progress = tqdm(total=len(track_ids))
    for track_id in track_ids:
        progress.set_description(get_track_description(track_id))
        progress.update(1)
    progress.close()
    return track_ids


def process_albums(album_ids):
    track_ids = []
    for album_id in album_ids:
        album_data = MyMelody.get_content_metadata("album", album_id)
        print(album_data["name"] + " - " + "; ".join([x["name"] for x in album_data["artists"]]))
        track_ids += process_tracks([x["id"] for x in album_data["tracks"]["items"]])
    return track_ids


def process_artists(artist_ids):
    track_ids = []
    for artist_id in artist_ids:
        artist_data = get_artist_metadata(artist_id)
        print(artist_data["name"])
        album_ids = []
        offset = 0
        limit = 50
        while True:
            args = {
                "limit": limit,
                "offset": offset,
                "include_groups": "single,album"
            }
            albums = MyMelody.get_content_metadata("artist_albums", artist_id, args)
            album_ids += [x["id"] for x in albums["items"]]
            if len(albums["items"]) < limit:
                break
            offset += limit
        track_ids += process_albums(album_ids)
    return track_ids


################################################################################
# CLI                                                                          #
################################################################################

@click.group()
def main():
    pass

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
@click.option(
    "--artists",
    required=False,
    default="",
    help="Comma separated list of artist ids",
)
@click.option(
    "--explicit",
    required=False,
    default=False,
    help="Only download the content passed",
)
def download(tracks, albums, artists, explicit):
    MyMelody()
    all_tracks = []

    if tracks:
        print("Processing tracks...")
        all_tracks += process_tracks(tracks.split(","))
        print()
    if albums:
        print("Processing albums...")
        all_tracks += process_albums(albums.split(","))
        print()
    if artists:
        print("Processing artists...")
        all_tracks += process_artists(artists.split(","))
        print()

    if not explicit:
        return

    print("Downloading tracks")
    download_tracks_safely(all_tracks)
    print()
    print("Cleaning up tracks and dirs")
    cleanup_tracks()
    MyMelody.write_data()

if __name__ == "__main__":
    main()

# TODO
# Support for playlists
# Search for songs of artist, from album, from playlist
# download only currently specified + download every eligible track