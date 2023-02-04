from spotify_download import SpotifyDownload
import json
from track import Track, TrackEncoder, TrackDecoder

sd = SpotifyDownload("user-library-read")
sc = sd.get_client()
# for album in [
#     [album["name"], album["uri"]]
#     for album in sc.artist_albums("06HL4z0CvFAxyc27GXpf02")["items"]
# ]:
#     print(album)

albums = []
while True:
    results = sc.artist_albums(
        "2eam0iDomRHGBypaDQLwWI", offset=len(albums), album_type="album,single"
    )["items"]
    albums += results
    if len(results) != 20:
        break

print(len(albums))

with open("tsalbums.json", "w") as of:
    for album in albums:
        print(album["name"], album["uri"], album["album_group"])
    json.dump(albums, of, indent=4)

# sc.import_json("cummulative.json")
# # sc.import_json("kerry.json")
# # sc.playlist("1NAUwTZ75h9e6wPVmyF2aO", "C:\\Users\\rasthmatic\\Music")
# # sc.export_json("kerry.json")
# # sc.export_json("testa.json")
# # print(sc.import_json("test.json"))
# mdir = "C:\\Users\\rasthmatic\\Music"
# sc.album("3KzAvEXcqJKBF97HrXwlgf", mdir)
# sc.album("1aYdiJk6XKeHWGO3FzHHTr", mdir)
# sc.album("6wCttLq0ADzkPgtRnUihLV", mdir)
# sc.album("1vANZV20H5B4Fk6yf7Ot9a", mdir)
# sc.album("0PT5m6hwPRrpBwIHVnvbFX", mdir)
# sc.album("50o7kf2wLwVmOTVYJOTplm", mdir)
# sc.album("3PRoXYsngSwjEQWR5PsHWR", mdir)
# sc.album("6QaVfG1pHYl1z15ZxkvVDW", mdir)
# sc.album("2BtE7qm1qzM80p9vLSiXkj", mdir)
# sc.album("1klALx0u4AavZNEvC4LrTL", mdir)
# sc.album("0ETFjACtuP2ADo6LFhL6HN", mdir)
# sc.album("0jTGHV5xqHPvEcwL8f6YU5", mdir)
# sc.export_json("cummulative.json")
