from abc import ABC, abstractmethod
from mymelody.database_connection import DatabaseConnection
from mymelody.to_database import MyMelodyDatabase


class SpotifyObject(ABC):
    def __init__(self, id):
        self.id = id
        self.db = MyMelodyDatabase()

    @abstractmethod
    def download(self):
        pass


class Track(SpotifyObject):
    def __init__(self, id):
        super().__init__(id)
        self._set_metadata()
        print(self.metadata)

    def _artist_from_data(self):
        self.metadata["artist"] = "; ".join(
            [artist["name"] for artist in self.metadata["artists"]]
        )

    def _albumartist_from_data(self):
        self.metadata["albumartist"] = [
            artist["name"]
            for artist in [album["artists"] for album in self.metadata["albums"]][0]
        ]

    def _album_from_data(self):
        self.metadata["album"] = "; ".join(
            [album["title"] for album in self.metadata["albums"]]
        )

    def _set_metadata(self):
        self.metadata = self.db.get_track(self.id)
        self._artist_from_data()
        self._album_from_data()
        self._albumartist_from_data()
        # print(self.metadata)

    def get_metadata(self, key):
        return self.metadata.get(key)

    def download(self):
        pass


class Album(SpotifyObject):
    def __init__(self, id):
        super().__init__(id)

    def download(self):
        return super().download()


class Artist(SpotifyObject):
    def __init__(self, id):
        super().__init__(id)

    def download(self):
        return super().download()
