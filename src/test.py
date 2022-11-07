from spotify_download import SpotifyDownload
import json
from track import Track, TrackEncoder, TrackDecoder

sc = SpotifyDownload("user-library-read")
sc.track("7BmpRLqZg1vLheYi1SI1Rw")
sc.track("7BmpRLqZg1vLheYi1SI1Rw")
# sc.album("76oMr4Y2pOtcrvZLc2ZikF")
sc.track("2pfEVSZdq5McocgAYWhgLu")
sc.track("4713WnRYJ0AY1qexk8o1Hd")
sc.export_json("test.json")
print(sc.import_json("test.json"))
