import yt_dlp
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import requests
import urllib.request

urls = ["https://m.youtube.com/watch?v=gGwN25z7FrE"]
images = "https://i.scdn.co/image/ab67616d0000b273e0b60c608586d88252b8fbc0"

ydl_opts = {
    "format": "mp3/bestaudio/best",
    "outtmpl": "%(title)s.%(ext)s",
    # "writethumbnail": True,
    "postprocessors": [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
        # {"key": "FFmpegMetadata", "add_metadata": True},
        # {"key": "EmbedThumbnail", "already_have_thumbnail": False},
    ],
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    error_code = ydl.download(urls)


img_data = requests.get(images).content
audio = MP3("Anti-Hero.mp3", ID3=ID3)
# print(audio.getall("APIC"))
audio.tags["APIC"] = APIC(
    encoding=3, mime="image/jpeg", type=3, desc=u'Cover', data=img_data
    # encoding=3, mime="image/jpeg", type=3, desc=u'Cover', data=urllib.request.urlopen(urllib.request.Request(images)).read()
)
audio.save()

# audio = ID3("Anti-Hero.mp3")
# audio.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Front over", data=img_data))
# audio.save(v2_version=3)

audio = MP3("Anti-Hero.mp3", ID3=EasyID3)
audio["tracknumber"] = "50"
audio.save()
