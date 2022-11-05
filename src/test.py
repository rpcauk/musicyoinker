from spotify_download import SpotifyDownload

sc = SpotifyDownload("user-library-read")
sc.download_track("7BmpRLqZg1vLheYi1SI1Rw")
print(sc._config["tracks"])
