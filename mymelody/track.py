import json
from typing import Any

from ytmusicapi import YTMusic

from mymelody.utils import track_length


class Track:
    def __init__(self, track_id, output_dir, spotify=None, json=None) -> None:
        self.id = track_id
        if spotify:
            self._metadata = self._metadata(spotify)
            self._extra_metadata = self._extra_metadata(spotify)
            self._output_file = self._output_file(output_dir)
        elif json:
            self.metadata = json["metadata"]
            self.output_file = json["output_file"]
            self.artwork_url = json["artwork_url"]
            self.download_url = json["download_url"]
        else:
            raise Exception("Either spotify or json, not both")

    def _metadata(self, resp):
        return {
            "title": resp["name"] + (" [E]" if resp["explicit"] else ""),
            "artist": "; ".join([artist["name"] for artist in resp["artists"]]),
            "album": resp["album"]["name"],
            "albumartist": "; ".join(
                [artist["name"] for artist in resp["album"]["artists"]]
            ),
            "length": track_length(resp["duration_ms"]),
            "date": resp["album"]["release_date"],
            "discnumber": str(resp["disc_number"]),
            "tracknumber": str(resp["track_number"]),
        }

    def _extra_metadata(self, resp):
        return {
            "download_url": self._download_url(),
            "artwork_url": self._artwork_url(resp["album"]["images"]),
            "explicit": resp["explicit"],
        }

    def _output_file(self, output_dir):
        file_name = "".join(e for e in self.title if e.isalnum())
        file_album = "".join(e for e in self.album if e.isalnum())
        file_artist = "".join(
            e for e in self.metadata["albumartist"].split("; ")[0] if e.isalnum()
        )
        return f"{output_dir}\\{file_artist}\\{file_album}\\{file_name}.mp3"

    def _artwork_url(self, album_images):
        max_image = sorted(album_images, key=lambda i: i["height"], reverse=True)[0]
        return max_image["url"]

    def _download_url(self):
        ytm = YTMusic()
        artist = self.artist.split(";")[0]
        album = self.album
        title = self.title
        yid = ytm.search(f"{artist} {album} {title}", filter="songs")[0]["videoId"]
        return f"m.youtube.com/watch?v={yid}"

    @property
    def metadata(self):
        return self._metadata

    @property
    def extra_metadata(self):
        return self._extra_metadata

    @property
    def title(self):
        return self.metadata["title"]

    @property
    def artist(self):
        return self.metadata["artist"]

    @property
    def album(self):
        return self.metadata["album"]

    @property
    def albumartist(self):
        return self.metadata["albumartist"]

    @property
    def length(self):
        return self.metadata["length"]

    @property
    def date(self):
        return self.metadata["date"]

    @property
    def discnumber(self):
        return self.metadata["discnumber"]

    @property
    def tracknumber(self):
        return self.metadata["tracknumber"]

    @property
    def download_url(self):
        return self.extra_metadata["download_url"]

    @property
    def artwork_url(self):
        return self.extra_metadata["artwork_url"]

    @property
    def explicit(self):
        return self.extra_metadata["explicit"]

    @property
    def output_file(self):
        return self._output_file

    def __repr__(self) -> str:
        return (
            f"{self.metadata['title']} "
            + f"by {self.metadata['artist']} "
            + f"from {self.metadata['album']} "
            + f"[{self.id}]"
        )

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, Track):
            return self.id == __o.id
        return False

    def __hash__(self) -> int:
        return hash(self.id)


class TrackEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, Track):
            return vars(o)
        else:
            return super().default(o)


class TrackDecoder(json.JSONDecoder):
    def __init__(self):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook)

    def object_hook(self, dct):
        if "id" in dct:
            return Track(dct["id"], dct["output_file"], json=dct)
        else:
            return dct
