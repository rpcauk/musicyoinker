import yt_dlp
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import requests
import json
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from datetime import datetime

os.environ["SPOTIPY_CLIENT_ID"] = "0124eb5e28344b1994d6e7fece490afa"
os.environ["SPOTIPY_CLIENT_SECRET"] = "399537abb2be43cea872fd07eeee2306"

urls = ["https://m.youtube.com/watch?v=REsc54NTz1A"]
images = "https://i.scdn.co/image/ab67616d0000b273e0b60c608586d88252b8fbc0"
example = """{
  "album": {
    "album_type": "album",
    "artists": [
      {
        "external_urls": {
          "spotify": "https://open.spotify.com/artist/06HL4z0CvFAxyc27GXpf02"
        },
        "href": "https://api.spotify.com/v1/artists/06HL4z0CvFAxyc27GXpf02",
        "id": "06HL4z0CvFAxyc27GXpf02",
        "name": "Taylor Swift",
        "type": "artist",
        "uri": "spotify:artist:06HL4z0CvFAxyc27GXpf02"
      }
    ],
    "available_markets": [
      "no"
    ],
    "external_urls": {
      "spotify": "https://open.spotify.com/album/3lS1y25WAhcqJDATJK70Mq"
    },
    "href": "https://api.spotify.com/v1/albums/3lS1y25WAhcqJDATJK70Mq",
    "id": "3lS1y25WAhcqJDATJK70Mq",
    "images": [
      {
        "height": 64,
        "url": "https://i.scdn.co/image/ab67616d00004851e0b60c608586d88252b8fbc0",
        "width": 64
      },
      {
        "height": 300,
        "url": "https://i.scdn.co/image/ab67616d00001e02e0b60c608586d88252b8fbc0",
        "width": 300
      },
      {
        "height": 640,
        "url": "https://i.scdn.co/image/ab67616d0000b273e0b60c608586d88252b8fbc0",
        "width": 640
      }
    ],
    "name": "Midnights (3am Edition)",
    "release_date": "2022-10-22",
    "release_date_precision": "day",
    "total_tracks": 20,
    "type": "album",
    "uri": "spotify:album:3lS1y25WAhcqJDATJK70Mq"
  },
  "artists": [
    {
      "external_urls": {
        "spotify": "https://open.spotify.com/artist/06HL4z0CvFAxyc27GXpf02"
      },
      "href": "https://api.spotify.com/v1/artists/06HL4z0CvFAxyc27GXpf02",
      "id": "06HL4z0CvFAxyc27GXpf02",
      "name": "Taylor Swift",
      "type": "artist",
      "uri": "spotify:artist:06HL4z0CvFAxyc27GXpf02"
    }
  ],
  "available_markets": [
    "no"
  ],
  "disc_number": 1,
  "duration_ms": 200690,
  "explicit": false,
  "external_ids": {
    "isrc": "USUG12205736"
  },
  "external_urls": {
    "spotify": "https://open.spotify.com/track/02Zkkf2zMkwRGQjZ7T4p8f"
  },
  "href": "https://api.spotify.com/v1/tracks/02Zkkf2zMkwRGQjZ7T4p8f",
  "id": "02Zkkf2zMkwRGQjZ7T4p8f",
  "is_local": false,
  "name": "Anti-Hero",
  "popularity": 88,
  "preview_url": null,
  "track_number": 3,
  "type": "track",
  "uri": "spotify:track:02Zkkf2zMkwRGQjZ7T4p8f"
}"""

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=os.environ["SPOTIPY_CLIENT_ID"],
        client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
    )
)


def track_length(milliseconds):
    length = ""
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    if hours:
        length = f"{hours}:"
    return f"{length}{minutes%60}:{seconds%60}"


# resp = sp.track("02Zkkf2zMkwRGQjZ7T4p8f")
resp = sp.track("6ADDIJxxqzM9LMpm78yzQG")
covers = {}
sresp = {
    "albumartist": "; ".join([artist["name"] for artist in resp["album"]["artists"]]),
    "album": resp["album"]["name"],
    "date": resp["album"]["release_date"],
    "artist": "; ".join([artist["name"] for artist in resp["artists"]]),
    "discnumber": str(resp["disc_number"]),
    "length": track_length(resp["duration_ms"]),
    "title": resp["name"],
    "tracknumber": str(resp["track_number"]),
}
if sresp["album"] not in covers:
    cover_url = sorted(resp["album"]["images"], key=lambda i: i["height"])[0]["url"]
    covers[resp["album"]["id"]] = requests.get(cover_url).content
print(sresp)

# ydl_opts = {
#     "format": "mp3/bestaudio/best",
#     "outtmpl": f"{sresp['title']}.mp3",
#     "postprocessors": [
#         {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
#     ],
# }

# with yt_dlp.YoutubeDL(ydl_opts) as ydl:
#     error_code = ydl.download(urls)

audio = MP3(f"{sresp['title']}.mp3", ID3=EasyID3)
for attribue in sresp.keys():
    audio[attribue] = sresp[attribue]
audio.save()

audio = MP3(f"{sresp['title']}.mp3", ID3=ID3)
audio.tags["APIC"] = APIC(
    encoding=3,
    mime="image/jpeg",
    type=3,
    desc="Cover",
    data=covers[resp["album"]["id"]],
)
audio.save()
