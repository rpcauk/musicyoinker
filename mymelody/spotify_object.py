from abc import ABC, abstractmethod
from mymelody.to_database import MyMelodyDatabase
from mymelody.spotipy_client import create_client
import re
import os
import pathlib
from mymelody.download import download, set_artwork, set_metadata


class SpotifyObject(ABC):
    def __init__(self, id):
        self.id = id
        self.db = MyMelodyDatabase(create_client(["user-library-read"]))

    @abstractmethod
    def download(self):
        pass

    @abstractmethod
    def validate(self):
        pass


class Track(SpotifyObject):
    def __init__(self, id):
        super().__init__(id)
        self.metadata = self._set_metadata()
        self.track_metadata = self._set_track_metadata()

    def _set_metadata(self):
        metadata = self.db.get_track(self.id)
        home_dir = "/home/ryan/music"
        rpl_str = "[^0-9a-zA-Z]+"
        nartist = re.sub(rpl_str, "", metadata["artists"][0]["name"])
        nalbum = re.sub(rpl_str, "", metadata["album"]["title"])
        ntitle = re.sub(rpl_str, "", metadata["title"])
        metadata["output_file"] = f"{home_dir}/{nartist}/{nalbum}/{ntitle}.mp3"
        return metadata

    def _set_track_metadata(self):
        track_metadata = {}
        track_metadata["title"] = self.metadata["title"]
        track_metadata["date"] = self.metadata["date"]
        track_metadata["discnumber"] = self.metadata["discnumber"]
        track_metadata["tracknumber"] = self.metadata["tracknumber"]
        track_metadata["artist"] = self._artist_string(self.metadata["artists"])
        track_metadata["album"] = self.metadata["album"]["title"]
        track_metadata["albumartist"] = self._albumartist_string(self.metadata["album"])
        return track_metadata

    def _artist_string(self, artists):
        return "; ".join([artist["name"] for artist in artists])

    def _albumartist_string(self, album):
        return self._artist_string(album["artists"])

    def download(self, validate=False):
        print(f"Downloading {self.metadata['title']}...")
        if not self.metadata["download_url"]:
            print(f"Skipping {self.metadata['title']} [No download_url]")
            return

        # Make sure path to file exists
        pathlib.Path(os.path.dirname(self.metadata["output_file"])).mkdir(
            parents=True, exist_ok=True
        )
        if os.path.exists(self.metadata["output_file"]):
            print(f"Skipping {self.metadata['title']} [Already exists]")
            return

        if validate:
            self.validate()

        download(
            self.metadata["download_url"], self.metadata["output_file"].split(".")[0]
        )
        set_metadata(self.track_metadata, self.metadata["output_file"])
        set_artwork(self.metadata["artwork_url"], self.metadata["output_file"])

    def validate(self, force=False, download=True):
        if self.db.is_validated(self.metadata["id"]) and not force:
            return
        print(
            f"{self.track_metadata['title']} by {self.track_metadata['artist']} from {self.track_metadata['album']}"
        )
        print("http://" + self.metadata["download_url"])
        new_download = input("New id? ")
        if not new_download:
            self.db.validate_track(self.metadata["id"])
            return
        self.db.validate_track(
            self.metadata["id"], f"m.youtube.com/watch?v={new_download}"
        )
        self.metadata["download_url"] = f"m.youtube.com/watch?v={new_download}"
        if os.path.exists(self.metadata["output_file"]):
            os.remove(self.metadata["output_file"])
        if download:
            self.download()


class Album(SpotifyObject):
    def __init__(self, id):
        super().__init__(id)
        self.metadata = self._set_metadata()
        self.tracks = self._get_tracks()

    def _set_metadata(self):
        metadata = self.db.get_album(self.id)
        return metadata

    def _get_tracks(self):
        return [Track(track) for track in self.db.get_album_tracks(self.id)]

    def download(self, validate=False):
        for track in self.tracks:
            track.download(validate=validate)

    def validate(self, download=False):
        for track in self.tracks:
            track.validate(download=download)


class Artist(SpotifyObject):
    def __init__(self, id):
        super().__init__(id)
        self.metadata = self._set_metadata()
        self.albums = self._get_albums()

    def _set_metadata(self):
        metadata = self.db.get_artist(self.id)
        return metadata

    def _get_albums(self):
        return [
            Album(album) for album in self.db.get_artist_albums(self.metadata["id"])
        ]

    def download(self, validate=False):
        for album in self.albums:
            album.download(validate=validate)

    def validate(self, download=False):
        for album in self.albums:
            album.validate(download=download)
