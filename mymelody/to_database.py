import sqlite3

from mymelody.create_db import initialise_db
from mymelody.spotipy_client import create_client
from mymelody.track import get_track_metadata
from mymelody.album import get_album_metadata
from mymelody.artist import get_artist_metadata


class MyMelodyDatabase:
    def __init__(self, spotipy_client) -> None:
        initialise_db("mm.db")
        self.conn = sqlite3.connect("mm.db")
        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()
        self.spotipy_client = spotipy_client

    def __del__(self):
        self.conn.close()

    def add_track(self, id: str) -> None:
        track_data = self.spotipy_client.track(id)
        db_data = self.c.execute(
            "SELECT title FROM tracks WHERE id = ?", (id,)
        ).fetchone()
        if db_data is None:
            track = get_track_metadata(track_data)
            print(f"Collecting track {track['title']} ...")

            sql = """
                INSERT INTO tracks (
                    id,
                    title,
                    length,
                    date,
                    discnumber,
                    tracknumber,
                    download_url,
                    artwork_url,
                    explicit
                ) 
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)"""

            self.c.execute(sql, list(track.values()))
            self.conn.commit()

        self.add_album(track_data["album"]["id"])
        album_tracks_sql = """
            INSERT OR IGNORE INTO album_tracks (
                track_id,
                album_id
            )
            VALUES(?, ?)
        """
        self.c.execute(album_tracks_sql, (id, track_data["album"]["id"]))
        self.conn.commit()
        for artist in track_data["artists"]:
            self.add_artist(artist["id"])
            track_artists_sql = """
                INSERT OR IGNORE INTO track_artists (
                    track_id,
                    artist_id
                )
                VALUES(?,?)
            """
            self.c.execute(track_artists_sql, (id, artist["id"]))
            self.conn.commit()

    def add_album(self, id):
        album_data = self.spotipy_client.album(id)
        db_data = self.c.execute(
            "SELECT title FROM albums WHERE id = ?", (id,)
        ).fetchone()
        if db_data is None:
            album = get_album_metadata(album_data)
            print(f"Collecting album {album['name']} ...")
            sql = """
                INSERT INTO albums (
                    id,
                    title,
                    date,
                    total_tracks,
                    artwork_url,
                    explicit
                ) 
                VALUES(?, ?, ?, ?, ?, ?)"""
            self.c.execute(
                sql,
                list(album.values()),
            )
            self.conn.commit()

        for artist in album_data["artists"]:
            self.add_artist(artist["id"])
            album_artists_sql = """
                INSERT OR IGNORE INTO album_artists (
                    album_id,
                    artist_id
                )
                VALUES(?,?)
            """
            self.c.execute(album_artists_sql, (id, artist["id"]))
            self.conn.commit()

    def add_artist(self, id):
        artist_data = self.spotipy_client.artist(id)
        db_data = self.c.execute(
            "SELECT name FROM artists WHERE id = ?", (id,)
        ).fetchone()
        if db_data is None:
            artist = get_artist_metadata(artist_data)
            print(f"Collecting artist {artist['name']} ...")
            sql = """
                INSERT INTO artists (
                    id,
                    name,
                    artwork_url
                ) 
                VALUES(?, ?, ?)"""
            self.c.execute(sql, list(artist.values()))
            self.conn.commit()

    def get_track(self, id):
        sql = """
            SELECT t.id, t.title
            FROM tracks t
            WHERE t.id = ?
        """

        track = dict(self.c.execute(sql, (id,)).fetchone())
        track["artists"] = self.get_track_artists(id)
        track["albums"] = self.get_track_albums(id)
        for album in track["albums"]:
            album["artists"] = self.get_album_artists(album["id"])
        # print(json.dumps(track, indent=4))

        # print(
        #     f"{track['title']} by {', '.join([artist['name'] for artist in track['artists']])} on {', '.join([album['title'] for album in track['albums']])}"
        # )
        return track

    def get_all_tracks(self):
        sql = """
            SELECT t.id, t.title
            FROM tracks t
        """

        return [
            self.get_track(track_id)
            for track_id in [
                dict(track)["id"] for track in self.c.execute(sql).fetchall()
            ]
        ]

    def get_artist_tracks(self, id):
        sql = """
            SELECT DISTINCT t.id, t.title
            FROM tracks t
            JOIN track_artists ta on ta.track_id = t.id
            JOIN artists a on ta.artist_id = a.id
            JOIN album_tracks at on at.track_id = t.id
            JOIN albums ab on at.album_id = ab.id
            JOIN album_artists aa on aa.album_id = ab.id
            JOIN artists aba on aa.artist_id = aba.id
            WHERE a.id = ?
        """

        return [
            self.get_track(track_id)
            for track_id in [
                dict(track)["id"] for track in self.c.execute(sql, (id,)).fetchall()
            ]
        ]

    def get_track_artists(self, id):
        sql = """
            SELECT a.id, a.name
            FROM tracks t
            JOIN track_artists ta on ta.track_id = t.id
            JOIN artists a on ta.artist_id = a.id
            WHERE t.id = ?
        """
        return [dict(row) for row in self.c.execute(sql, (id,)).fetchall()]

    def get_album_artists(self, id):
        sql = """
            SELECT a.id, a.name 
            FROM albums ab
            JOIN album_artists aa on aa.album_id = ab.id
            JOIN artists a on aa.artist_id = a.id
            WHERE ab.id = ?
        """
        return [dict(row) for row in self.c.execute(sql, (id,)).fetchall()]

    def get_track_albums(self, id):
        sql = """
            SELECT ab.id, ab.title
            FROM tracks t
            JOIN album_tracks at on at.track_id = t.id
            JOIN albums ab on at.album_id = ab.id
            WHERE t.id = ?
        """
        return [dict(row) for row in self.c.execute(sql, (id,)).fetchall()]

    def collect_album(self, id):
        album_tracks = [
            track["id"] for track in self.spotipy_client.album_tracks(id)["items"]
        ]
        for track_id in album_tracks:
            self.add_track(track_id)

    def collect_artist(self, id):
        album_ids = []
        while True:
            results = [
                album["id"]
                for album in self.spotipy_client.artist_albums(
                    id, offset=len(album_ids), album_type="album,single"
                )["items"]
            ]
            album_ids += results
            if len(results) != 20:
                break
        for album_id in album_ids:
            self.collect_album(album_id)


if __name__ == "__main__":
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
    # mmdb.add_track("6dGnYIeXmHdcikdzNNDMm2")
    # mmdb.add_track("2M4tVhRXucLE9M3STv21Yi")
    # mmdb.get_track("2M4tVhRXucLE9M3STv21Yi")
    mmdb.actually_add_album("3lS1y25WAhcqJDATJK70Mq")
    mmdb.get_all_tracks()
