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

    # @classmethod
    # def get_track(cls, track_id):
    #     return cls.CLIENT.track(track_id)

    # @classmethod
    # def get_album_tracks(cls, album, limit=50, offset=0):
    #     return

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
        print(f"\r  Sleep for {i + 1} second(s)...", end="")
        time.sleep(1)
    print()


################################################################################
# Metadata                                                                     #
################################################################################

def set_artist_metadata(artist, update=True):
    # existing_data = MyMelody.get_data("artists", artist["id"])
    # if existing_data:
    #     return existing_data

    # resp = MyMelody.get_content_metadata("artist", artist_id)
    data = {}
    data["name"] = artist["name"]
    data["artwork_url"] = sorted(artist["images"], key=lambda i: i["height"], reverse=True)[0]["url"]
    data["follow"] = True

    if update:
        MyMelody.update_data("artists", artist["id"], data)
    return data


def set_track_metadata(track, update=True):
    # existing_data = MyMelody.get_data("tracks", track_id)
    # if existing_data:
    #     return existing_data

    # track_data = MyMelody.get_content_metadata("track", track_id)
    track_data = {}
    track_data["name"] = track["name"]

    match track["album"]["release_date_precision"]:
        case "day":
            track_data["release_date"] = track["album"]["release_date"]
        case "month":
            track_data["release_date"] = track["album"]["release_date"] + "-01"
        case "year":
            track_data["release_date"] = track["album"]["release_date"] + "-01-01"

    track_data["disc_number"] = str(track["disc_number"])
    track_data["track_number"] = str(track["track_number"])
    track_data["album"] = {
        "id": track["album"]["id"],
        "name": track["album"]["name"],
        "artists": {x["id"]: {k:v for k,v in x.items() if k in ("name")} for x in track["album"]["artists"]},
        "album_type": track["album"]["album_type"]
    }
    track_data["artists"] = {x["id"]: {k:v for k,v in x.items() if k in ("name")} for x in track["artists"]}
    track_data["artwork_url"] = sorted(track["album"]["images"], key=lambda i: i["height"], reverse=True)[0]["url"]
    track_data["ignore"] = False

    if update:
        MyMelody.update_data("tracks", track["id"], track_data)
    return track_data


def get_track_description(track_id, album=False, artists=True):
    track_data = MyMelody.get_data("tracks", track_id)
    track_name = track_data["name"]
    track_album = track_data["album"]["name"]
    track_artists = "; ".join([x["name"] for x in track_data["artists"].values()])
    track_string = track_name
    if album:
        track_string += " - " + track_album
    if artists:
        track_string += " - " + track_artists
    return track_string


def get_track_path(track_id):
    track_data = MyMelody.get_data("tracks", track_id)
    track_path = MyMelody.get_track_path()
    for k,v in track_data['album']['artists'].items():
        track_path += f"/{sanitize_name(v['name'])} [{k}]"
    track_path += f"/{sanitize_name(track_data['album']['name'])} [{track_data['album']['id']}]"
    track_path += f"/{sanitize_name(track_data['name'])} [{track_id}].mp3"
    return track_path


################################################################################
# Download                                                                     #
################################################################################

def tracks_to_download():
    track_ids = []
    for track_id, track_data in MyMelody.get_data("tracks").items():
        track_path = get_track_path(track_id)
        if track_data["ignore"] or os.path.exists(track_path):
            continue
        track_ids.append(track_id)
    return track_ids

def set_track_tags(track_id):
    track_data = MyMelody.get_data("tracks", track_id)
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
    track_data = MyMelody.get_data("tracks", track_id)
    track_path = get_track_path(track_id)

    if track_data["ignore"] or os.path.exists(track_path):
        print(f"  Skipping {get_track_description(track_id)}")
        return False

    pathlib.Path(os.path.dirname(track_path)).mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile() as fh:
        stream = MyMelody.get_content_stream(TrackId.from_uri(f"spotify:track:{track_id}"))
        total_size = stream.input_stream.size
        progress = tqdm(total=total_size, desc="  "+get_track_description(track_id))
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
    downloaded = 0
    for i in range(len(track_ids)):
        if downloaded != 0:
            if downloaded % 100 == 0:
                antiban_wait(seconds=60)
            elif downloaded % 50 == 0:
                antiban_wait(seconds=30)
            elif downloaded % 25 == 0:
                antiban_wait(seconds=10)
            elif downloaded % 5 == 0:
                antiban_wait(seconds=5)
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
        print()

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
        print()


################################################################################
# Process                                                                      #
################################################################################

def process_tracks(track_ids):
    tracks = {}
    chunk_size = 50
    chunks = [track_ids[i:i+chunk_size] for i in range(0,len(track_ids),chunk_size)]

    # progress = tqdm(total=len(track_ids)) # , disable=(not update)
    for chunk in chunks:
        # track_data = set_track_metadata(MyMelody.CLIENT.track(track_id))
        # tracks[track_id] = track_data
        # progress.set_description(get_track_description(track_id))
        # progress.update(1)
        tracks = MyMelody.CLIENT.tracks(chunk)
        for track in tracks["tracks"]:
            tracks[track["id"]] = set_track_metadata(track)
            print("  " + get_track_description(track["id"]))
    # progress.close()
    return tracks


def process_albums(album_ids):
    tracks = {}
    chunk_size = 20
    chunks = [album_ids[i:i+chunk_size] for i in range(0,len(album_ids),chunk_size)]
    for chunk in chunks:
        # album_data = MyMelody.CLIENT.album(album_id)
        # print(album_data["name"] + " - " + "; ".join([x["name"] for x in album_data["artists"]]))
        # tracks |= process_tracks([x["id"] for x in album_data["tracks"]["items"]], update=update)
        
        albums = MyMelody.CLIENT.albums(chunk)
        for album in albums["albums"]:
            print("  " + album["name"] + " - " + "; ".join([x["name"] for x in album["artists"]]))
            album_sans_tracks = {k:v for k,v in album.items() if k not in ("tracks")}
            for track in album["tracks"]["items"]:
                track["album"] = album_sans_tracks
                tracks[track["id"]] = set_track_metadata(track)
                print("    " + get_track_description(track["id"]))
    return tracks


def process_artists(artist_ids):
    SORT_ORDER = {
        "album": 0,
        "single": 1,
        "compilation": 2,
        "appears_on": 3,
    }
    tracks = {}
    for artist_id in artist_ids:
        artist_data = set_artist_metadata(MyMelody.CLIENT.artist(artist_id))
        print("  " + artist_data["name"])

        existing_tracks = {k:v for k,v in MyMelody.get_data("tracks").items() if artist_id in v["artists"]}

        artist_albums = []
        artist_tracks = []
        sorted_tracks = []

        # Get all albums containing track by artist
        artist_albums_limit = 50
        artist_albums_offset = 0
        artist_albums_total = MyMelody.CLIENT.artist_albums(artist_id, limit=1)["total"]
        artist_albums_progress = tqdm(total=artist_albums_total, desc="  Albums")
        while True:
            artist_albums_resp = MyMelody.CLIENT.artist_albums(artist_id, limit=artist_albums_limit, offset=artist_albums_offset)["items"]
            artist_albums_progress.update(len(artist_albums_resp))
            artist_albums += artist_albums_resp
            if len(artist_albums_resp) < artist_albums_limit:
                break
            artist_albums_offset += artist_albums_limit
        artist_albums_progress.close()

        # Get all tracks, from those albums, by artist
        album_chunk_size = 20
        album_ids = [x["id"] for x in artist_albums]
        album_chunks = [album_ids[i:i+album_chunk_size] for i in range(0,len(album_ids),album_chunk_size)]
        album_progress = tqdm(total=len(album_ids))
        for chunk in album_chunks:
            albums = MyMelody.CLIENT.albums(chunk)
            for album in albums["albums"]:
                album_progress.set_description("  "+album["name"])
                album_sans_tracks = {k:v for k,v in album.items() if k not in ("tracks")}
                tracks_by_artist = [x for x in album["tracks"]["items"] if artist_id in [y["id"] for y in x["artists"]]]
                for track in tracks_by_artist:
                    track["album"] = album_sans_tracks
                    artist_tracks.append(track)
                album_progress.update(1)
        album_progress.close()

        # Sorting tracks to remove duplicates from fluff albums
        for track in artist_tracks:
            if [x for x in existing_tracks.values() if x["name"] == track["name"]]:
                continue
            tracks_same_name = [x for x in sorted_tracks if x["name"] == track["name"]] + [track]
            ordered_tracks = [i for i in sorted(tracks_same_name, key=lambda x: (artist_id in x["album"]["artists"], SORT_ORDER[x["album"]["album_type"]], x["album"]["release_date"]))]
            sorted_tracks = [x for x in sorted_tracks if x not in ordered_tracks] + [ordered_tracks[0]]

        print()
        print("  Tracks:")
        if not sorted_tracks:
            print("    No new tracks")
            continue
        for track in sorted(sorted_tracks, key=lambda x: x["album"]["release_date"]):
            tracks[track["id"]] = set_track_metadata(track)
            print("    " + get_track_description(track["id"], album=True, artists=True))
    return tracks


def pull_artists():
    for artist_id, artist_data in MyMelody.get_data("artists").items():
        artist_tracks = process_artists([artist_id], update=False)
        track_diff = [x for x in artist_tracks if x not in MyMelody.get_data("tracks")]
        # track_diff = {k:v for k,v in MyMelody.get_data("tracks").items() if k not in artist_tracks and artist_id in v["album"]["artists"]}
        if not track_diff:
            continue
        print(f"Missing {len(track_diff)} tracks from {artist_data['name']}:")
        for track_id in track_diff:
            print("  " + get_track_description(track_id, album=True, artists=False))


################################################################################
# CLI                                                                          #
################################################################################

@click.group()
def main():
    MyMelody()

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
    download_tracks = []

    if tracks:
        print("Processing tracks...")
        download_tracks += process_tracks(tracks.split(","))
        print()
    if albums:
        print("Processing albums...")
        download_tracks += process_albums(albums.split(","))
        print()
    if artists:
        print("Processing artists...")
        download_tracks += process_artists(artists.split(","))
        print()

    if not explicit:
        download_tracks = tracks_to_download()

    cleanup_tracks()
    MyMelody.write_data()

    if download_tracks:
        print(f"Downloading {len(download_tracks)} tracks:")
        download_tracks_safely(download_tracks)

@main.command()
@click.argument("artist")
def pull_artist(artist):
    # process_artists([artist])
    # MyMelody.write_data()
    # MyMelody.CLIENT.search("")
    # pull_artists()
    pass

if __name__ == "__main__":
    main()

# TODO
# Support for playlists
# Search for songs of artist, from album, from playlist
# download only currently specified + download every eligible track