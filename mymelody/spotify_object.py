from abc import ABC, abstractmethod
from mymelody.to_database import MyMelodyDatabase
from mymelody.spotipy_client import create_client
import re
import os
import pathlib
from mymelody.download import download, set_artwork, set_metadata
import json


class RetrievalException(Exception):
    pass


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

    @abstractmethod
    def data(self, simplify):
        pass


class Track(SpotifyObject):
    def __init__(self, id, collect=False, data={}):
        super().__init__(id)
        if data:
            self.metadata = self._set_metadata(self.db.manual_add_track(id, data))
        elif collect:
            self.metadata = self._set_metadata(self.db.collect_track(id))
        else:
            self.metadata = self._set_metadata(self.db.get_track(id))
        if not self.metadata:
            raise RetrievalException(f"Could not retrieve Track [{id}]")
        self.track_metadata = self._set_track_metadata()

    def _set_metadata(self, metadata):
        # TODO: Get this from somewhere reasonable
        home_dir = "/home/ryan/music"
        rpl_str = "[^0-9a-zA-Z]+"
        nartist = re.sub(rpl_str, "", metadata["artists"][0]["name"])
        nalbum = re.sub(rpl_str, "", metadata["album"]["title"])
        ntitle = re.sub(rpl_str, "", metadata["title"])
        metadata["output_file"] = f"{home_dir}/{nartist}/{nalbum}/{ntitle}.mp3"
        metadata["hidden"] = metadata["hidden"]
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

    def collect(self):
        return

    def download(self, force=False, validate=False):
        print(f"Downloading {self.metadata['title']}...")
        if not self.metadata["download_url"]:
            print(f"Skipping {self.metadata['title']} [No download_url]")
            return

        # Make sure path to file exists
        pathlib.Path(os.path.dirname(self.metadata["output_file"])).mkdir(
            parents=True, exist_ok=True
        )
        if os.path.exists(self.metadata["output_file"]) and not force:
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

    def data(self, simple=False) -> str:
        if self.metadata["hidden"]:
            return {}
        if simple:
            return {"id": self.id, "title": self.metadata["title"]}
        return self.metadata

    def update(self, values):
        return self.db.update_track(self.id, values)

    def delete(self):
        self.db.delete_track(self.id)
        self.metadata = {}
        self.track_metadata = {}


class Album(SpotifyObject):
    def __init__(self, id, collect=False, data={}):
        super().__init__(id)
        if data:
            self.metadata = self._set_metadata(self.db.manual_add_album(id, data))
            self.metadata["tracks"] = self._get_tracks()
        elif collect:
            self.metadata = self._set_metadata(self.db.collect_album(id))
            self.metadata["tracks"] = self._get_tracks(collect=True)
        else:
            self.metadata = self._set_metadata(self.db.get_album(id))
            self.metadata["tracks"] = self._get_tracks()
        if not self.metadata:
            raise RetrievalException(f"Could not retrieve Album [{id}]")

    def _set_metadata(self, metadata):
        return metadata

    def _get_tracks(self, collect=False):
        tracks = [
            Track(track["id"], collect=collect) for track in self.metadata["tracks"]
        ]
        return sorted(
            tracks, key=lambda track: int(track.track_metadata["tracknumber"])
        )

    # def collect(self, validate=True):
    #     self.metadata["tracks"] = self._get_tracks(collect=True)
    #     if validate:
    #         self.validate()

    def download(self, validate=True, all=False):
        # self.metadata["tracks"] = self._get_tracks()
        print("hel")
        for track in self.metadata["tracks"]:
            if not all and track.metadata["hidden"]:
                continue
            track.download(validate=validate)

    def validate(self, download=False):
        print(f"[Album] Validating {self.metadata['title']}")
        for track in self.metadata["tracks"]:
            track.validate(download=download)

    def data(self, simple=False, artists=False, tracks=False):
        data = self.metadata
        if simple:
            return {"id": self.id, "title": self.metadata["title"]}
        if not artists:
            data.pop("artists")
        if not tracks:
            data.pop("tracks")
        else:
            data["tracks"] = list(
                filter(
                    bool,
                    [track.data(simple=True) for track in data["tracks"]],
                )
            )
        return data

    def update(self, values):
        return self.db.update_album(self.id, values)

    def delete(self):
        self.db.delete_album(self.id)
        self.metadata = {}

    def hidden(self):
        return [
            track for track in self.metadata["tracks"] if track.metadata["hidden"]
        ] == self.metadata["tracks"]


class Artist(SpotifyObject):
    def __init__(self, id, collect=False, data={}):
        super().__init__(id)
        if data:
            self.metadata = self._set_metadata(self.db.manual_add_artist(id, data))
        elif collect:
            self.metadata = self._set_metadata(self.db.collect_artist(id))
        else:
            self.metadata = self._set_metadata(self.db.get_artist(id))
        if not self.metadata:
            raise RetrievalException(f"Could not retrieve Artist [{id}]")
        self.metadata["albums"] = self._get_albums()
        self.metadata["tracks"] = self._get_tracks()

    def _set_metadata(self, metadata):
        return metadata

    def _get_albums(self, collect=False):
        # albums = self.metadata["albums"]
        # album_data = []
        # for album in albums:
        #     collect_album = input(f"Collect album {album['id']}? [y/n]")
        #     if collect_album == "y":
        #         album_data.append(Album(album["id"]))
        # return album_data
        return [
            Album(album["id"], collect=collect) for album in self.metadata["albums"]
        ]

    def _get_tracks(self, collect=False):
        return [
            Track(track["id"], collect=collect) for track in self.metadata["tracks"]
        ]

    def collect(self, validate=True):
        # self.metadata = self.db.collect_artist(self.id)
        self.metadata["albums"] = self._get_albums(collect=True)
        self.metadata["tracks"] = self._get_tracks(collect=True)
        # print(self.metadata["albums"])
        if validate:
            self.validate()

    def download(self, validate=True):
        for track in self.metadata["tracks"]:
            if not bool(track.metadata["hidden"]):
                track.download(validate=validate)

    def validate(self, download=False):
        for album in self.metadata["albums"]:
            album.validate(download=download)
        for track in self.metadata["tracks"]:
            track.validate(download=download)

    def data(self, albums=False, tracks=False):
        data = self.metadata
        if not albums:
            data.pop("albums")
        else:
            data["albums"] = [
                album.data(simple=True)
                for album in data["albums"]
                if not album.hidden()
            ]
        if not tracks:
            data.pop("tracks")
        else:
            data["tracks"] = list(
                filter(
                    bool,
                    [track.data(simple=True) for track in data["tracks"]],
                )
            )
        return data

    def update(self, values):
        return self.db.update_artist(self.id, values)
