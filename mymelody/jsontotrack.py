import json
from mutagen.id3 import ID3, APIC, COMM
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
import yt_dlp
import requests
import os


def update_artwork(music_file, artwork_url):
    audio = MP3(music_file, ID3=ID3)
    if artwork_url != audio.tags["COMM:artwork_url:ENG"]:
        print(f"Updating artwork...")  # TODO
        print(f"    {audio.tags['COMM:artwork_url:ENG']} -> {artwork_url}")

        audio.tags.pop("APIC:Cover")
        audio.tags.pop("COMM:artwork_url:ENG")

        audio.tags["APIC"] = APIC(
            encoding=0,
            mime="image/jpeg",
            type=3,
            desc="Cover",
            data=requests.get(artwork_url).content,
        )
        audio.tags["COMM:AWU:ENG"] = COMM(
            encoding=0,
            lang="ENG",
            desc="artwork_url",
            text=[artwork_url],
        )
    audio.save()


def update_metadata(music_file, metadata):
    audio = MP3(music_file, ID3=EasyID3)
    for metadata_key, metadata_value in metadata.items():
        if metadata_value != audio[metadata_key][0]:
            print(f"Updating {metadata_key}...")  # TODO
            print(f"    {audio[metadata_key][0]} -> {metadata_value}")
            audio[metadata_key] = metadata_value
    audio.save()


def update_source(music_file, download_url, metadata, artwork_url):
    audio = MP3(music_file, ID3=ID3)
    if download_url != audio.tags["COMM:download_url:ENG"]:
        print(f"Updating music source...")  # TODO
        print(f"    {audio.tags['COMM:download_url:ENG']} -> {download_url}")

        os.remove(music_file)

        ydl_opts = {
            "format": "mp3/bestaudio/best",
            "outtmpl": music_file,
            # "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
            ],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            error_code = ydl.download(download_url)

        audio.tags["COMM:DLU:ENG"] = COMM(
            encoding=0,
            lang="ENG",
            desc="download_url",
            text=[download_url],
        )

        audio.save()
        update_metadata(music_file, metadata)
        update_artwork(music_file, artwork_url)


with open("state_20221103203843.json") as json_file:
    data = json.load(json_file)

    for track_id, track_config in data.items():
        music_file = track_config["file"]
        download_url = track_config["download_url"]
        artwork_url = track_config["artwork_url"]
        metadata = track_config["metadata"]
        update_source(
            music_file=music_file,
            download_url=download_url,
            metadata=metadata,
            artwork_url=artwork_url,
        )
        update_artwork(music_file=music_file, artwork_url=artwork_url)
        update_metadata(music_file=music_file, metadata=metadata)
