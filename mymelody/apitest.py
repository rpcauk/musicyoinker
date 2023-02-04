from ytmusicapi import YTMusic
import json

ytm = YTMusic()
x = ytm.search("Taylor Swift Midnights You're on your own kid", filter="songs", limit=5)
for i in x:
    print(i["title"])
    print(i["videoId"])
    print([x["name"] for x in i["artists"]])
# print(json.dumps(x, indent=4))
