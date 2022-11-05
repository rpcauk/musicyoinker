from spotify_download import SpotifyDownload

sc = SpotifyDownload("user-library-read")
resp = sc._spotipy_client.track("7BmpRLqZg1vLheYi1SI1Rw")
print(resp)
