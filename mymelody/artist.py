from collections import OrderedDict


def get_artist_metadata(resp):
    artist_metadata = OrderedDict()
    artist_metadata["id"] = resp["id"]
    artist_metadata["name"] = resp["name"]
    try:
        artist_metadata["artwork_url"] = sorted(
            resp["images"], key=lambda i: i["height"], reverse=True
        )[0]["url"]
    except:
        artist_metadata["artwork_url"] = ""
    return artist_metadata
