from spotify_download import SpotifyDownload
import json
from track import Track, TrackEncoder, TrackDecoder

sc = SpotifyDownload("user-library-read")
sc.track("7BmpRLqZg1vLheYi1SI1Rw")
sc.track("7BmpRLqZg1vLheYi1SI1Rw")
sc.album("3lS1y25WAhcqJDATJK70Mq")
print(sc.tracks)
print(len(sc.artwork))

# # with open(f"config_test.json", "w") as cf:
# #     json.dump(sc._config["tracks"], cf, cls=TrackEncoder, indent=4)

# with open("config_test.json") as json_file:
#     data = json.load(json_file, cls=TrackDecoder)
#     # print(type(data["7BmpRLqZg1vLheYi1SI1Rw"]))
#     print(data)
#     # for track_id, track_data in data.items():
#     #     print(Track(track_id, None, json=track_data))
