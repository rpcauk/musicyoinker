from spotify_download import SpotifyDownload
import json
from track import Track, TrackEncoder, TrackDecoder

sc = SpotifyDownload("user-library-read")
sc.track("7BmpRLqZg1vLheYi1SI1Rw")
# sc.track("7BmpRLqZg1vLheYi1SI1Rw")
sc.album("3lS1y25WAhcqJDATJK70Mq")
sc.export_json("test.json")
sc.import_json("test.json")
