from collections import OrderedDict

from dateutil import parser
from ytmusicapi import YTMusic

from mymelody.utils import track_length


def _artwork_url(resp):
    album_images = resp["album"]["images"]
    max_image = sorted(album_images, key=lambda i: i["height"], reverse=True)[0]
    return max_image["url"]


def _download_url(resp):
    ytm = YTMusic()
    artist = resp["artists"][0]["name"]
    album = resp["album"]["name"]
    title = (resp["name"],)
    yid = ytm.search(f"{artist} {album} {title}", filter="songs")[0]["videoId"]
    return f"m.youtube.com/watch?v={yid}"


def get_track_metadata(resp):
    track_data = OrderedDict()
    track_data["id"] = resp["id"]
    track_data["title"] = resp["name"] + (" [E]" if resp["explicit"] else "")
    track_data["length"] = track_length(resp["duration_ms"])
    track_data["date"] = parser.parse(resp["album"]["release_date"]).strftime(
        "%Y-%m-%d"
    )
    track_data["discnumber"] = str(resp["disc_number"])
    track_data["tracknumber"] = str(resp["track_number"])
    track_data["download_url"] = _download_url(resp)
    track_data["artwork_url"] = _artwork_url(resp)
    track_data["explicit"] = resp["explicit"]
    return track_data
