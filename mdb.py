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
import sqlite3
from tabulate import tabulate
import subprocess
import re

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
    def get_db_path(cls):
        return cls.CONFIG.get("db_path")

    @classmethod
    def get_track_path(cls):
        return cls.CONFIG.get("track_path")


################################################################################
# Database                                                                     #
################################################################################

CREATE_TRACKS_TABLE = """
CREATE TABLE IF NOT EXISTS tracks (
    id TEXT,
    album_id TEXT,
    artist_id TEXT,
    name TEXT,
    disc_number INTEGER,
    track_number INTEGER,
    hidden INTEGER,
    explicit INTEGER,
    PRIMARY KEY (id, album_id, artist_id)
    FOREIGN KEY (album_id) REFERENCES albums(id)
    FOREIGN KEY (artist_id) REFERENCES artists(id)
)
"""
CREATE_ALBUMS_TABLE = """
CREATE TABLE IF NOT EXISTS albums (
    id TEXT,
    artist_id TEXT,
    name TEXT,
    album_type TEXT,
    total_tracks INTEGER,
    release_date TEXT,
    artwork_url TEXT,
    hidden INTEGER,
    PRIMARY KEY (id, artist_id)
    FOREIGN KEY (artist_id) REFERENCES artists(id)
)
"""
CREATE_ARTISTS_TABLE = """
CREATE TABLE IF NOT EXISTS artists (
    id TEXT,
    name TEXT,
    follow INTEGER DEFAULT 0,
    hidden INTEGER,
    PRIMARY KEY (id)
)
"""
CREATE_PLAYLISTS_TABLE = """
CREATE TABLE IF NOT EXISTS playlists (
    id TEXT,
    track_id TEXT,
    track_order INTEGER,
    name TEXT,
    artwork_url TEXT,
    PRIMARY KEY (id, track_id, track_order),
    FOREIGN KEY (track_id) REFERENCES tracks(id)
)
"""

class MusicDatabase:
    CONNECTION = None
    CURSOR = None

    # def __init__(self):
    #     pass

    @classmethod
    def create_db(cls, db_path):
        pathlib.Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
        cls.CONNECTION = sqlite3.connect(db_path)
        cls.CONNECTION.row_factory = sqlite3.Row
        cls.CURSOR = cls.CONNECTION.cursor()
        cls.CURSOR.execute(CREATE_ARTISTS_TABLE)
        cls.CURSOR.execute(CREATE_ALBUMS_TABLE)
        cls.CURSOR.execute(CREATE_TRACKS_TABLE)
        cls.CURSOR.execute(CREATE_PLAYLISTS_TABLE)
        cls.CONNECTION.commit()

    @classmethod
    def close(cls):
        cls.CURSOR.close()
        cls.CONNECTION.close()


    # TRACKS
    @classmethod
    def get_track(cls, track_id):
        tracks_by_artist = cls.CURSOR.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchall()
        if not tracks_by_artist:
            return []
        tracks_by_artist = [dict(x) for x in tracks_by_artist]
        track = tracks_by_artist[0]
        track["album"] = MusicDatabase.get_album(track.pop("album_id"))
        track["artists"] = [MusicDatabase.get_artist(x["artist_id"]) for x in tracks_by_artist]
        track.pop("artist_id")
        return track

    @classmethod
    def get_all_tracks(cls):
        unique_ids = list(set([x["id"] for x in cls.CURSOR.execute("SELECT id FROM tracks").fetchall()]))
        return [MusicDatabase.get_track(x) for x in unique_ids]

    @classmethod
    def add_track(cls, track, replace=False):
        existing_track = MusicDatabase.get_track(track["id"])
        if existing_track:
            if replace or (not existing_track["explicit"] and track.get("explicit", True)):
                track = existing_track
            else:
                return existing_track

        MusicDatabase.add_album(track["album"])
        for track_artist in [MusicDatabase.add_artist(x) for x in track["artists"]]:
            cls.CURSOR.execute(
                "INSERT OR REPLACE INTO tracks (id, album_id, artist_id, name, disc_number, track_number, hidden, explicit) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    track["id"],
                    track["album"]["id"],
                    track_artist["id"],
                    track["name"],
                    track["disc_number"],
                    track["track_number"],
                    int(track.get("hidden", False)),
                    int(track.get("explicit", True)),
                )
            )

        cls.CONNECTION.commit()
        return MusicDatabase.get_track(track["id"])

    @classmethod
    def remove_track(cls, track_id, delete=False):
        try:
            if delete:
                cls.CURSOR.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
                # Check and cleanup artists and albums
            else:
                MusicDatabase.add_track({"id": track_id, "hidden": True}, replace=True)
            return True
        except:
            return False


    # ALBUMS
    @classmethod
    def get_album(cls, album_id):
        albums_by_artist = cls.CURSOR.execute("SELECT * FROM albums WHERE id = ?", (album_id,)).fetchall()
        if not albums_by_artist:
            return []
        albums_by_artist = [dict(x) for x in albums_by_artist]
        album = albums_by_artist[0]
        album["artists"] = [MusicDatabase.get_artist(x["artist_id"]) for x in albums_by_artist]
        album.pop("artist_id")
        return album

    @classmethod
    def get_all_albums(cls):
        return [MusicDatabase.get_album(x["id"]) for x in cls.CURSOR.execute("SELECT id FROM albums").fetchall()]

    @classmethod
    def get_all_album_tracks(cls, album_id):
        album = MusicDatabase.get_album(album_id)
        if not album:
            return []
        track_ids = list(set([dict(x) for x in cls.CURSOR.execute("SELECT id from tracks WHERE album_id = ?", (album_id,)).fetchall()]))
        return sorted([MusicDatabase.get_track(x) for x in track_ids], key=lambda x: x["track_number"])

    @classmethod
    def add_album(cls, album, hidden=False, replace=False):
        existing_album = MusicDatabase.get_album(album["id"])
        if existing_album and not replace:
            return existing_album

        match album["release_date_precision"]:
            case "day":
                release_date = album["release_date"]
            case "month":
                release_date = album["release_date"] + "-01"
            case "year":
                release_date = album["release_date"] + "-01-01"

        for album_artist in [MusicDatabase.add_artist(x) for x in album["artists"]]:
            cls.CURSOR.execute(
                "INSERT OR REPLACE INTO albums (id, artist_id, name, album_type, total_tracks, release_date, artwork_url, hidden) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    album["id"],
                    album_artist["id"],
                    album["name"],
                    album["album_type"],
                    album["total_tracks"],
                    release_date,
                    sorted(album["images"], key=lambda i: i["height"], reverse=True)[0]["url"],
                    int(hidden),
                )
            )

        cls.CONNECTION.commit()
        return MusicDatabase.get_album(album["id"])

    @classmethod
    def hide_album(cls, album):
        hidden_album = MusicDatabase.add_album(album, hidden=True, replace=True)


    # ARTISTS
    @classmethod
    def get_artist(cls, artist_id):
        artist = cls.CURSOR.execute("SELECT * FROM artists WHERE id = ?", (artist_id,)).fetchone()
        if not artist:
            return []
        artist = dict(artist)
        return artist

    @classmethod
    def get_all_artists(cls):
        return [MusicDatabase.get_artist(x["id"]) for x in cls.CURSOR.execute("SELECT id FROM artists").fetchall()]

    # TODO
    @classmethod
    def get_all_artist_tracks(cls, album_id):
        album = MusicDatabase.get_album(album_id)
        if not album:
            return []
        track_ids = list(set([dict(x) for x in cls.CURSOR.execute("SELECT id from tracks WHERE album_id = ?", (album_id,))]))
        return sorted([MusicDatabase.get_track(x) for x in track_ids], key=lambda x: x["track_number"])

    # TODO
    @classmethod
    def get_all_artist_albums(cls, album_id):
        album = MusicDatabase.get_album(album_id)
        if not album:
            return []
        track_ids = list(set([dict(x) for x in cls.CURSOR.execute("SELECT id from tracks WHERE album_id = ?", (album_id,))]))
        return sorted([MusicDatabase.get_track(x) for x in track_ids], key=lambda x: x["track_number"])

    @classmethod
    def add_artist(cls, artist, hidden=False, follow=False, replace=False):
        existing_artist = MusicDatabase.get_artist(artist["id"])
        if existing_artist and not replace:
            return existing_artist
        
        cls.CURSOR.execute(
            "INSERT OR REPLACE INTO artists (id, name, follow, hidden) VALUES (?, ?, ?, ?)",
            (
                artist["id"],
                artist["name"],
                int(follow),
                int(hidden),
            )
        )

        cls.CONNECTION.commit()
        return MusicDatabase.get_artist(artist["id"])

    
    # PLAYLISTS
    @classmethod
    def get_playlist(cls, playlist_id):
        playlist_tracks = cls.CURSOR.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,)).fetchall()
        if not playlist_tracks:
            return []
        playlist_tracks = sorted([dict(x) for x in playlist_tracks], key=lambda x: x["track_order"])
        # track_ids = list(set([dict(x) for x in cls.CURSOR.execute("SELECT track_id, order from tracks WHERE album_id = ?", (album_id,))]))
        playlist = {
            "id": playlist_id,
            "name": playlist_tracks[0]["name"],
            "artwork_url": playlist_tracks[0]["artwork_url"],
            "tracks": [MusicDatabase.get_track(x["track_id"]) for x in playlist_tracks]
        }
        return playlist
    
    @classmethod
    def add_playlist(cls, playlist):
        existing_playlist = MusicDatabase.get_playlist(playlist["id"])
        if existing_playlist and replace:
            MusicDatabase.remove_playlist(playlist["id"])
        
        tracks = playlist["tracks"]
        for track in tracks:
            track["explicit"] = False
        tracks = [MusicDatabase.add_track(x) for x in tracks]
        for i in range(len(tracks)):
            cls.CURSOR.execute(
                "INSERT OR REPLACE INTO playlists (id, track_id, track_order, name, artwork_url) VALUES (?, ?, ?, ?, ?)",
                (
                    playlist["id"],
                    tracks[i]["id"],
                    i+1,
                    playlist["name"],
                    sorted(playlist["images"], key=lambda i: i["height"], reverse=True)[0]["url"],
                )
            )

    @classmethod
    def remove_playlist(cls, playlist_id, delete=False):
        try:
            if delete:
                cls.CURSOR.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
                # Check and cleanup artists and albums
            else:
                # TODO: Hide all tracks that aren't explicit?
                MusicDatabase.add_track({"id": track_id, "hidden": True}, replace=True)
            cls.CONNECTION.commit()
            return True
        except:
            return False


        cls.CONNECTION.commit()
        return MusicDatabase.get_playlist(playlist["id"])


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


def get_track_description(track, album=False, album_artists=False, artists=True):
    track_name = track["name"]
    track_album = track["album"]["name"]
    track_album_artists = "; ".join(x["name"] for x in track["album"]["artists"])
    track_artists = "; ".join([x["name"] for x in track["artists"]])
    track_string = track_name
    if album:
        track_string += f" from {track_album}"
        if album_artists:
            track_string += f" ({track_album_artists})"
    if artists:
        track_string += f" by {track_artists}"
    return track_string


def get_track_path(track):
    track_path = MyMelody.get_track_path()
    track_path += f"/{sanitize_name(track['album']['artists'][0]['name'])} [{track['album']['artists'][0]['id']}]"
    track_path += f"/{sanitize_name(track['album']['name'])} [{track['album']['id']}]"
    track_path += f"/{sanitize_name(track['name'])} [{track['id']}].mp3"
    return track_path


################################################################################
# Download                                                                     #
################################################################################

def tracks_to_download():
    download = []
    for track in MusicDatabase.get_all_tracks():
        track_path = get_track_path(track)
        if track["hidden"] or os.path.exists(track_path):
            continue
        download.append(track)
    return download

def set_track_tags(track):
    track_path = get_track_path(track)

    track_tags = MP3(track_path, ID3=EasyID3)
    track_tags["album"] = track["album"]["name"]
    track_tags["albumartist"] = "; ".join([x["name"] for x in track["album"]["artists"]])
    track_tags["artist"] = "; ".join([x["name"] for x in track["artists"]])
    track_tags["discnumber"] = str(track["disc_number"])
    track_tags["tracknumber"] = str(track["track_number"])
    track_tags["title"] = track["name"]
    track_tags["date"] = track["album"]["release_date"]
    track_tags.save()
    track_tags = MP3(track_path, ID3=ID3)
    track_tags.tags["APIC"] = APIC(
        encoding=0,
        mime="image/jpeg",
        type=3,
        desc="Cover",
        data=requests.get(track["album"]["artwork_url"]).content,
    )
    track_tags.save()


def download_track(track):
    track_path = get_track_path(track)

    if track["hidden"] or os.path.exists(track_path):
        print(f"  Skipping {get_track_description(track)}")
        return False

    pathlib.Path(os.path.dirname(track_path)).mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile() as fh:
        stream = MyMelody.get_content_stream(TrackId.from_uri(f"spotify:track:{track['id']}"))
        total_size = stream.input_stream.size
        progress = tqdm(total=total_size, desc="  "+get_track_description(track))
        downloaded = 0
        fail_count = 0
        while downloaded < total_size:
            remaining = total_size - downloaded
            read_size = min(20000, remaining)

            try:
                data = stream.input_stream.stream().read(read_size)
            except IndexError as e:
                print(f"Stream download failed with id: {track['id']}")
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

    set_track_tags(track)
    return True


def download_tracks_safely(tracks):
    downloaded = 0
    for i in range(len(tracks)):
        if downloaded != 0:
            if downloaded % 100 == 0:
                antiban_wait(seconds=60)
            elif downloaded % 50 == 0:
                antiban_wait(seconds=30)
            elif downloaded % 25 == 0:
                antiban_wait(seconds=10)
            elif downloaded % 5 == 0:
                antiban_wait(seconds=5)
        download_resp = download_track(tracks[i])
        if download_resp:
            downloaded += 1


def cleanup_tracks():
    tracks = [x for x in MusicDatabase.get_all_tracks() if x["ignore"]]
    if tracks:
        print("Deleting tracks:")
        for track in tracks:
            track_path = get_track_path(track)
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
    tracks = []
    chunk_size = 50
    chunks = [track_ids[i:i+chunk_size] for i in range(0,len(track_ids),chunk_size)]

    for chunk in chunks:
        raw_tracks = MyMelody.CLIENT.tracks(chunk)
        for raw_track in raw_tracks["tracks"]:
            tracks.append(MusicDatabase.add_track(raw_track))
            print("  " + get_track_description(raw_track))
    return tracks


def process_albums(album_ids):
    tracks = []
    chunk_size = 20
    chunks = [album_ids[i:i+chunk_size] for i in range(0,len(album_ids),chunk_size)]
    for chunk in chunks:        
        albums = MyMelody.CLIENT.albums(chunk)
        for album in albums["albums"]:
            print("  " + album["name"] + " - " + "; ".join([x["name"] for x in album["artists"]]))
            album_sans_tracks = {k:v for k,v in album.items() if k not in ("tracks")}
            for track in album["tracks"]["items"]:
                track["album"] = album_sans_tracks
                tracks += MusicDatabase.add_track(track)
                print("    " + get_track_description(track))
    return tracks


def track_prompt(track, skip=False):
    if skip:
        action = "skip"
    else:
        action = "hide" if track.get("hidden", False) else "add"
    values = {
        "action": action,
        "id": track["id"],
        "name": track["name"],
        "artists": "; ".join([x["name"] for x in track["artists"]]),
        "track_number": str(track["track_number"]),
        "album": track["album"]["name"],
        "album_artists": "; ".join([x["name"] for x in track["album"]["artists"]]),
        "release_date": track["album"]["release_date"]
    }
    return values.values()


def process_artists(artist_ids):
    SORT_ORDER = {
        "album": 0,
        "single": 1,
        "compilation": 2,
    }
    tracks = []
    for artist_id in artist_ids:
        artist_data = MusicDatabase.add_artist(MyMelody.CLIENT.artist(artist_id), follow=True, replace=True)
        print("  " + artist_data["name"])

        existing_tracks = [x for x in MusicDatabase.get_all_tracks() if artist_data in x["artists"]]
        existing_tracks_ids = [x["id"] for x in existing_tracks]

        artist_albums = []
        artist_tracks = []
        other_tracks = []


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
                    if track["id"] in existing_tracks_ids:
                        continue
                    track["album"] = album_sans_tracks
                    if artist_id in [x["id"] for x in track["album"]["artists"]]:
                        artist_tracks.append(track)
                    else:
                        other_tracks.append(track)
                    
                album_progress.update(1)
        album_progress.close()


        # Sort tracks and decide what to download
        track_actions = {
            "existing": [],
            "add": [],
            "skip": [],
        }
        for track in sorted(artist_tracks, key=lambda x: (SORT_ORDER[x["album"]["album_type"]], x["album"]["release_date"])):
            if track["album"]["album_type"] in ("album", "compliation"):
                # Hide previous singles to make way for album
                for single_track in [x for x in existing_tracks if track["name"] == x["name"] and x["album"]["album_type"] == "single" and not x["hidden"]]:
                    single_track["hidden"] = True
                    track_actions["existing"].append(single_track)
            # Add single as hidden if already in existing album
            elif track["album"]["album_type"] == "single" and track["name"] in [x["name"] for x in existing_tracks+track_actions["add"] if x["album"]["album_type"] in ("album", "compliation")]:
                track["hidden"] = True
            # Add single as hidden if already exists earlier
            elif track["album"]["album_type"] == "single" and track["name"] in [x["name"] for x in existing_tracks+track_actions["add"] if x["album"]["album_type"] in ("single")]:
                track["hidden"] = True
            track_actions["add"].append(track)

        for track in sorted(other_tracks, key=lambda x: (SORT_ORDER[x["album"]["album_type"]], x["album"]["release_date"])):
            if track["name"] in [x["name"] for x in existing_tracks+track_actions["add"]]:
                track_actions["skip"].append(track)
                continue
            track_actions["add"].append(track)

        for taction, tdata in track_actions.items():
            tdata.sort(key=lambda x: (x["album"]["release_date"], x["album"]["name"], x["track_number"]))


        # Prompt user to confirm choice
        tracks_to_add = []
        with tempfile.NamedTemporaryFile(mode="w+") as fh:
            fh.write(f"# Tracks to download by {artist_data['name']}\n")
            fh.write("# List of actions:\n")
            fh.write("#   add - adds track metadata and downloads\n")
            fh.write("#   hide - adds track metadata but doesn't download\n")
            fh.write("#   skip - ignores track and doesn't add metadata\n")
            fh.write("\n")
            for track_action, track_data in track_actions.items():
                if not track_data:
                    continue
                if track_action == "existing":
                    fh.write("Modify existing tracks:\n")
                elif track_action == "add":
                    fh.write("Add tracks:\n")
                elif track_action == "skip":
                    fh.write("Skip tracks:\n")
                fh.write(tabulate([track_prompt(x, skip=track_action=="skip") for x in track_data], tablefmt="plain"))
                fh.write("\n\n")
                fh.flush()
            subprocess.run([os.getenv("EDITOR"), fh.name])
            fh.seek(0)
            for line in fh.readlines():
                regex = re.search("^(.*?) +(.*?) +.*", line)
                if regex and regex.group(1) in ("add", "hide"):

                    tracks_to_add += [x|{"hidden":regex.group(1)=="hide"} for x in track_actions["add"] if x["id"] == regex.group(2)]


        # Add the track metadata to database
        print()
        print("  Tracks:")
        if not artist_tracks:
            print("    No new tracks")
            continue
        for track in tracks_to_add:
            tracks.append(MusicDatabase.add_track(track, replace=hidden))
            if track["id"] not in existing_tracks_ids and track.get("hidden", False):
                continue
            modifier_str = "-" if track["id"] in existing_tracks_ids else "+"
            print(f"    {modifier_str}{get_track_description(track, album=True, artists=True)}")
    return tracks

def process_playlists(playlist_ids):
    tracks = []
    for playlist_id in playlist_ids:
        playlist = MyMelody.CLIENT.playlist(playlist_id)

        playlist_tracks = []

        # Get all tracks in playlist
        playlist_tracks_limit = 50
        playlist_tracks_offset = 0
        playlist_tracks_total = MyMelody.CLIENT.playlist_items(playlist_id, limit=1)["total"]
        playlist_tracks_progress = tqdm(total=playlist_tracks_total, desc="  Playlist tracks")
        while True:
            playlist_tracks_resp = MyMelody.CLIENT.playlist_items(playlist_id, limit=playlist_tracks_limit, offset=playlist_tracks_offset)["items"]
            playlist_tracks_progress.update(len(playlist_tracks_resp))
            playlist_tracks += playlist_tracks_resp
            if len(playlist_tracks_resp) < playlist_tracks_limit:
                break
            playlist_tracks_offset += playlist_tracks_limit
        playlist_tracks_progress.close()

        # for track in playlist_tracks:
        #     # Allows for tracks only added by playlist to be removed when removed from playlist
        #     track["explicit"] = False
        
        playlist["tracks"] = [x["track"] for x in playlist_tracks]
        tracks += MusicDatabase.add_playlist(playlist)["tracks"]
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
    MusicDatabase.create_db("z.db")

@main.command()
def download():
    """
    Downloads all the tracks in the database
    """
    tracks = tracks_to_download()
    print(f"Downloading {len(tracks)} tracks:")
    download_tracks_safely(tracks)
    MusicDatabase.close()

@main.command()
def credentials():
    """
    Generates a credentials.json file when casting from a premium account
    """
    zs = ZeroconfServer.Builder().create()
    print("Transfer playback from desktop client to librespot-python via Spotify Connect in order to store session")
    while True:
        time.sleep(1)
        if zs._ZeroconfServer__session:
            print(f"Grabbed {zs._ZeroconfServer__session} for {zs._ZeroconfServer__session.username()}")
            
            if pathlib.Path("credentials.json").exists():
                print("Session stored in credentials.json. Now you can Ctrl+C")
                break

@main.command()
def test():
    """
    Used to test random commands
    """
    # print(MusicDatabase.get_track("46b0Hj6XPgIrwKURVsZeVA"))
    # MusicDatabase.CURSOR.execute("DELETE FROM tracks WHERE album_id = ?", ("6P5NO5hzJbuOqSdyPB7SJM",))
    # MusicDatabase.CURSOR.execute("DELETE FROM albums WHERE id = ?", ("6P5NO5hzJbuOqSdyPB7SJM",))
    # MusicDatabase.CONNECTION.commit()
    print([x["id"] for x in MusicDatabase.CURSOR.execute("SELECT id FROM tracks").fetchall()])
    MusicDatabase.close()


################################################################################
# CLI - Tracks                                                                 #
################################################################################

@main.group("tracks")
def tracks_cli():
    """
    Manages tracks in database
    """
    pass

@tracks_cli.command("get")
@click.option("--ids", required=False, default="", help="Comma separated list of track ids")
@click.option("--show-ids", is_flag=True, default=False, help="Show track id")
def tracks_cli_get(ids, show_ids):
    """
    Lists tracks
    """
    if ids:
        tracks = [MusicDatabase.get_track(x) for x in ids.split(",")]
    else:
        tracks = MusicDatabase.get_all_tracks()
    tracks = sorted([x for x in tracks if not x["hidden"]], key=lambda x: (x["album"]["release_date"], x["album"]["name"], x["track_number"]))
    track_headers = ["name", "artists", "track_number", "album"]
    if show_ids:
        track_headers = ["id"] + track_headers
    tracks_to_show = []
    for track in tracks:
        track_data = [
            track["name"],
            "; ".join([x["name"] for x in track["artists"]]),
            track["track_number"],
            track["album"]["name"],
        ]
        if show_ids:
            track_data = [track["id"]] + track_data
        tracks_to_show.append(track_data)
    print(tabulate(tracks_to_show, headers=track_headers))
    MusicDatabase.close()

@tracks_cli.command("add")
@click.option("--ids", required=True, default="", help="Comma separated list of track ids")
@click.option("--force", is_flag=True, default=False, help="Unhides track if previously hidden")
@click.option("--no-download", is_flag=True, default=False, help="Only add tracks to database")
def tracks_cli_add(ids, force, no_download):
    """
    Adds tracks
    """
    # TODO: Add force
    print("Processing tracks...")
    tracks_to_add = process_tracks(ids.split(","))
    if not no_download:
        print()
        print(f"Downloading {len(tracks_to_add)} tracks:")
        download_tracks_safely(tracks_to_add)
    MusicDatabase.close()

@tracks_cli.command("remove")
@click.option("--ids", required=True, default="", help="Comma separated list of track ids")
@click.option("--delete", is_flag=True, default=False, help="Permanently removes track from database")
def tracks_cli_remove(ids, delete):
    """
    Deletes tracks
    """
    print("Deleting tracks...")
    for track_id in tracks:
        print(f"  {track_id}")
        MusicDatabase.remove_track(track_id, delete=delete)
    MusicDatabase.close()


################################################################################
# CLI - Artists                                                                #
################################################################################

@main.group("artists")
def artists_cli():
    """
    Manages artists in database
    """
    pass

@artists_cli.command("add")
@click.option("--ids", required=True, default="", help="Comma separated list of artist ids")
# @click.option("--force", is_flag=True, default=False, help="Unhides track if previously hidden")
@click.option("--no-download", is_flag=True, default=False, help="Only add tracks to database")
def artists_cli_add(ids, no_download):
    """
    Adds artists and all their tracks
    """
    print("Processing artists...")
    tracks_to_add = process_artists(ids.split(","))
    # if not no_download:
    #     print()
    #     print(f"Downloading {len(tracks_to_add)} tracks:")
    #     download_tracks_safely(tracks_to_add)
    MusicDatabase.close()

# TODO: Get artists
# TODO: Remove Artists

################################################################################
# CLI - Playlists                                                              #
################################################################################

@main.group("playlists")
def playlists_cli():
    """
    Manages playlists in database
    """
    pass

@playlists_cli.command("get")
@click.option("--ids", required=True, default="", help="Comma separated list of playlist ids")
@click.option("--show-ids", is_flag=True, default=False, help="Show track id")
def playlists_cli_get(ids, show_ids):
    """
    Lists tracks in playlists
    """
    # if ids:
    #     tracks = [MusicDatabase.get_track(x) for x in ids.split(",")]
    # else:
    #     tracks = MusicDatabase.get_all_tracks()
    playlist = MusicDatabase.get_playlist(ids)
    tracks = [x for x in playlist["tracks"] if not x["hidden"]]
    track_headers = ["order", "name", "artists", "album"]
    if show_ids:
        track_headers = ["id"] + track_headers
    tracks_to_show = []
    for i in range(len(tracks)):
        track_data = [
            i+1,
            tracks[i]["name"],
            "; ".join([x["name"] for x in tracks[i]["artists"]]),
            tracks[i]["album"]["name"],
        ]
        if show_ids:
            track_data = [track["id"]] + track_data
        tracks_to_show.append(track_data)
    print(tabulate(tracks_to_show, headers=track_headers))
    MusicDatabase.close()

@playlists_cli.command("add")
@click.option("--ids", required=True, default="", help="Comma separated list of playlist ids")
@click.option("--no-download", is_flag=True, default=False, help="Only add tracks to database")
def playlists_cli_add(ids, no_download):
    """
    Adds playlists and all their tracks
    """
    print("Procesing playlists")
    tracks_to_add = process_playlists(ids.split(","))
    MusicDatabase.close()

@playlists_cli.command("remove")
@click.option("--ids", required=True, default="", help="Comma separated list of playlist ids")
# @click.option("--no-download", is_flag=True, default=False, help="Only add tracks to database")
def playlists_cli_remove(ids):
    """
    Deletes playlists and their tracks that are only part of the playlist
    """
    print("Deleting playlists...")
    for playlist_id in ids.split(","):
        print(f"  {playlist_id}")
        # MusicDatabase.remove_playlist(playlist_id, delete=True)
        MusicDatabase.CURSOR.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        MusicDatabase.CONNECTION.commit()
    MusicDatabase.close()

if __name__ == "__main__":
    main()

# TODO
# Support for playlists
# Search for songs of artist, from album, from playlist
# download only currently specified + download every eligible track