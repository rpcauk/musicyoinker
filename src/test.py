from spotify_download import SpotifyDownload
import json
from track import Track, TrackEncoder, TrackDecoder

sc = SpotifyDownload("user-library-read")
# sc.track("7BmpRLqZg1vLheYi1SI1Rw")
# sc.track("7BmpRLqZg1vLheYi1SI1Rw")
# sc.album("1j3pIPXjLIFkp84OfVUsNT")
# sc.track("2pfEVSZdq5McocgAYWhgLu")
# sc.track("4713WnRYJ0AY1qexk8o1Hd")
sc.playlist("3h0105n5BQxWFU7QJhaRvC")
sc.export_json("validate.json")
# print(sc.import_json("test.json"))


# import time
# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys

# browser = webdriver.Chrome()
# browser.get("https://www.artofmanliness.com")
# browser.execute_script("window.open('about:blank','secondtab');")
# browser.switch_to.window("secondtab")
# browser.get("https://ryanpcadams.com/")
# for x in range(10):
#     try:
#         print(browser.current_url)
#         time.sleep(2)
#     except Exception as e:
#         print("tab has been closed")
#         break

# print("done-so")
# time.sleep(10)
