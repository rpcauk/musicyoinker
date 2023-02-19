import sqlite3
from sqlite3 import Cursor
from mymelody.track import Track
from mymelody.spotify_download import SpotifyDownload
from dateutil import parser
import json


class MyMelodyDatabase:
    def __init__(self) -> None:
        self.conn = sqlite3.connect("mm.db")
        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()
        self._initialise_tables()
        _sd = SpotifyDownload("user-library-read")
        self.sc = _sd.get_client()

    def __del__(self):
        self.conn.close()

    def _initialise_tables(self):
        self.c.execute(
            """
                CREATE TABLE IF NOT EXISTS tracks (
                    id text PRIMARY KEY,
                    title text NOT NULL,
                    length text NOT NULL,
                    date text,
                    discnumber text,
                    tracknumber text,
                    download_url text NOT NULL,
                    artwork_url text NOT NULL,
                    explicit boolean NOT NULL DEFAULT 0,
                    validated boolean DEFAULT 0,
                    hidden boolean DEFAULT 0
                );
            """
        )
        self.c.execute(
            """
                CREATE TABLE IF NOT EXISTS albums (
                    id text PRIMARY KEY,
                    title text NOT NULL,
                    date text,
                    total_tracks text,
                    explicit boolean NOT NULL DEFAULT 0,
                    artwork_url text NOT NULL
                )
            """
        )
        self.c.execute(
            """
                CREATE TABLE IF NOT EXISTS artists (
                    id text PRIMARY KEY,
                    name text NOT NULL,
                    artwork_url text NOT NULL
                )
            """
        )
        self.c.execute(
            """
                CREATE TABLE IF NOT EXISTS  playlists (
                    id text PRIMARY KEY,
                    name text NOT NULL,
                    owner text,
                    artwork_url text NOT NULL
                )
            """
        )
        self.c.execute(
            """
                CREATE TABLE IF NOT EXISTS track_artists (
                    track_id INTEGER,
                    artist_id INTEGER,
                    FOREIGN KEY(track_id) REFERENCES tracks(id),
                    FOREIGN KEY(artist_id) REFERENCES artists(id),
                    PRIMARY KEY (track_id, artist_id)
                )
            """
        )
        self.c.execute(
            """
                CREATE TABLE IF NOT EXISTS album_tracks (
                    track_id INTEGER,
                    album_id INTEGER,
                    FOREIGN KEY(track_id) REFERENCES tracks(id),
                    FOREIGN KEY(album_id) REFERENCES albums(id),
                    PRIMARY KEY (track_id, album_id)
                )
            """
        )
        self.c.execute(
            """
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    track_id INTEGER,
                    playlist_id INTEGER,
                    FOREIGN KEY(track_id) REFERENCES tracks(id),
                    FOREIGN KEY(playlist_id) REFERENCES playlists(id),
                    PRIMARY KEY (track_id, playlist_id)
                )
            """
        )
        self.c.execute(
            """
                CREATE TABLE IF NOT EXISTS album_artists (
                    album_id INTEGER,
                    artist_id INTEGER,
                    FOREIGN KEY(album_id) REFERENCES albums(id),
                    FOREIGN KEY(artist_id) REFERENCES artists(id),
                    PRIMARY KEY (album_id, artist_id)
                )
            """
        )

    def add_track(self, id: str) -> None:
        db_data = self.c.execute(
            "SELECT title FROM tracks WHERE id = ?", (id,)
        ).fetchone()
        track_data = self.sc.track(id)
        if db_data is None:
            track = Track(id, "/home/ryan/music", spotify=track_data)

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
            self.c.execute(
                sql,
                [
                    track.id,
                    track.title,
                    track.length,
                    track.date,
                    track.discnumber,
                    track.tracknumber,
                    track.download_url,
                    track.artwork_url,
                    track.explicit,
                ],
            )
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
        album_data = self.sc.album(id)
        db_data = self.c.execute(
            "SELECT title FROM albums WHERE id = ?", (id,)
        ).fetchone()
        if db_data is None:
            album_explicit = any(
                [bool(track["explicit"]) for track in album_data["tracks"]["items"]]
            )
            album_metadata = [
                id,
                album_data["name"] + (" [E]" if album_explicit else ""),
                parser.parse(album_data["release_date"]).strftime("%Y-%m-%d"),
                album_data["total_tracks"],
                album_explicit,
                sorted(album_data["images"], key=lambda i: i["height"], reverse=True)[
                    0
                ]["url"],
            ]
            sql = """
                INSERT INTO albums (
                    id,
                    title,
                    date,
                    total_tracks,
                    explicit,
                    artwork_url
                ) 
                VALUES(?, ?, ?, ?, ?, ?)"""
            self.c.execute(
                sql,
                album_metadata,
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
        artist_data = self.sc.artist(id)
        db_data = self.c.execute(
            "SELECT name FROM artists WHERE id = ?", (id,)
        ).fetchone()
        if db_data is None:
            sql = """
                INSERT INTO artists (
                    id,
                    name,
                    artwork_url
                ) 
                VALUES(?, ?, ?)"""
            self.c.execute(
                sql,
                [
                    id,
                    artist_data["name"],
                    sorted(
                        artist_data["images"], key=lambda i: i["height"], reverse=True
                    )[0]["url"],
                ],
            )
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

        print(
            f"{track['title']} by {', '.join([artist['name'] for artist in track['artists']])} on {', '.join([album['title'] for album in track['albums']])}"
        )

    def get_all_tracks(self):
        sql = """
            SELECT t.id, t.title
            FROM tracks t
        """

        for track_id in [dict(track)["id"] for track in self.c.execute(sql).fetchall()]:
            self.get_track(track_id)

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

    def actually_add_album(self, id):
        album_tracks = [track["id"] for track in self.sc.album_tracks(id)["items"]]
        for track_id in album_tracks:
            self.add_track(track_id)


if __name__ == "__main__":
    mmdb = MyMelodyDatabase()
    # mmdb.add_track("6dGnYIeXmHdcikdzNNDMm2")
    # mmdb.add_track("2M4tVhRXucLE9M3STv21Yi")
    # mmdb.get_track("2M4tVhRXucLE9M3STv21Yi")
    mmdb.actually_add_album("3lS1y25WAhcqJDATJK70Mq")
    mmdb.get_all_tracks()
