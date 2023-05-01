from collections import OrderedDict
from dateutil import parser


def get_album_metadata(resp):
    album_metadata = OrderedDict()
    album_metadata["id"] = resp["id"]
    album_metadata["name"] = resp["name"] + (" [E]" if is_explicit(resp) else "")
    album_metadata["date"] = parser.parse(resp["release_date"]).strftime("%Y-%m-%d")
    album_metadata["total_tracks"] = resp["total_tracks"]
    album_metadata["artwork_url"] = sorted(
        resp["images"], key=lambda i: i["height"], reverse=True
    )[0]["url"]
    album_metadata["explicit"] = is_explicit(resp)
    return album_metadata


def is_explicit(resp):
    return any([bool(track["explicit"]) for track in resp["tracks"]["items"]])
