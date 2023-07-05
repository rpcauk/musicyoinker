import sqlite3

from mymelody.create_db import initialise_db
from mymelody.spotipy_client import create_client
from mymelody.track_helper import get_track_metadata
from mymelody.album import get_album_metadata
from mymelody.artist import get_artist_metadata
from mymelody.database_connection import Singleton


class MyMelodyDatabase(metaclass=Singleton):
    def __init__(self, spotipy_client) -> None:
        initialise_db("mm.db")
        self.conn = sqlite3.connect("mm.db")
        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()
        self.spotipy_client = spotipy_client

    def __del__(self):
        self.conn.close()

    ############################################################################
    # ADD TO DATABASE                                                          #
    ############################################################################
    def add_track(self, id: str) -> None:
        # Get Track data from Spotify
        track_data = self.spotipy_client.track(id)
        track = get_track_metadata(track_data)
        print(f"Collecting track {track['title']} ...")

        # Add it to database
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

        # Add Album to database
        self.add_album(track_data["album"])

        # Add link between track and album
        album_tracks_sql = """
            INSERT OR IGNORE INTO album_tracks (
                track_id,
                album_id
            )
            VALUES(?, ?)
        """
        self.c.execute(album_tracks_sql, (id, track_data["album"]["id"]))
        self.conn.commit()

        # Add all Artists to database
        for artist in track_data["artists"]:
            self.add_artist(artist)

            # Add link between track and artists
            track_artists_sql = """
                INSERT OR IGNORE INTO track_artists (
                    track_id,
                    artist_id
                )
                VALUES(?,?)
            """
            self.c.execute(track_artists_sql, (id, artist["id"]))
            self.conn.commit()
        return self.get_track(id)

    def add_album(self, album):
        db_data = self.c.execute(
            "SELECT title FROM albums WHERE id = ?", (album["id"],)
        ).fetchone()
        if db_data is None:
            spotify_album = self.spotipy_client.album(album["id"])
            album_data = get_album_metadata(spotify_album)
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
                list(album_data.values()),
            )
            self.conn.commit()

        for artist in album["artists"]:
            self.add_artist(artist)
            album_artists_sql = """
                INSERT OR IGNORE INTO album_artists (
                    album_id,
                    artist_id
                )
                VALUES(?,?)
            """
            self.c.execute(album_artists_sql, (album["id"], artist["id"]))
            self.conn.commit()

    def add_artist(self, artist):
        db_data = self.c.execute(
            "SELECT name FROM artists WHERE id = ?", (artist["id"],)
        ).fetchone()
        if db_data is None:
            # artist_data = self.spotipy_client.artist(artist["id"])
            artist_data = get_artist_metadata(artist)
            print(f"Collecting artist {artist['name']} ...")
            sql = """
                INSERT INTO artists (
                    id,
                    name,
                    artwork_url
                ) 
                VALUES(?, ?, ?)"""
            self.c.execute(sql, list(artist_data.values()))
            self.conn.commit()

    ############################################################################
    # Get                                                                      #
    ############################################################################
    def get_track(self, id):
        track = self.c.execute("SELECT * FROM tracks WHERE id = ?", (id,)).fetchone()

        if track:
            track = dict(track)
            track["artists"] = self.get_track_artists(id)
            track["album"] = self.get_track_album(id)
            track["album"]["artists"] = self.get_album_artists(track["album"]["id"])
            return track
        else:
            return self.add_track(id)

    def get_album(self, id):
        album_tracks = [
            str(track["id"]) for track in self.spotipy_client.album_tracks(id)["items"]
        ]
        for track_id in album_tracks:
            self.get_track(track_id)
        return dict(
            self.c.execute("SELECT * FROM albums WHERE id = ?", (id,)).fetchone()
        )

    def get_artist(self, id):
        album_ids = []
        while True:
            results = [
                str(album["id"])
                for album in self.spotipy_client.artist_albums(
                    id,
                    limit=50,
                    offset=len(album_ids),
                    album_type="album,single,compilation",
                )["items"]
            ]
            album_ids += results
            if len(results) != 50:
                break

        for album_id in album_ids:
            self.get_album(album_id)
        return dict(
            self.c.execute("SELECT * FROM artists WHERE id = ?", (id,)).fetchone()
        )

    # def get_all_tracks(self):
    #     sql = """
    #         SELECT t.id, t.title
    #         FROM tracks t
    #     """

    #     return [
    #         self.get_track(track_id)
    #         for track_id in [
    #             dict(track)["id"] for track in self.c.execute(sql).fetchall()
    #         ]
    #     ]

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

    def get_album_tracks(self, id):
        sql = """
            SELECT at.track_id 
            FROM album_tracks at
            WHERE at.album_id = ?
        """
        return [dict(row)["track_id"] for row in self.c.execute(sql, (id,)).fetchall()]

    def get_artist_albums(self, id):
        sql = """
            SELECT aa.album_id 
            FROM album_artists aa
            WHERE aa.artist_id = ?
        """
        return [dict(row)["album_id"] for row in self.c.execute(sql, (id,)).fetchall()]

    def get_track_album(self, id):
        sql = """
            SELECT ab.id, ab.title
            FROM tracks t
            JOIN album_tracks at on at.track_id = t.id
            JOIN albums ab on at.album_id = ab.id
            WHERE t.id = ?
        """
        return [dict(row) for row in self.c.execute(sql, (id,)).fetchall()][0]

    ############################################################################
    # Validate                                                                 #
    ############################################################################
    def is_validated(self, id):
        sql_validated = """
            SELECT validated
            FROM tracks
            WHERE id = ?;
        """
        return bool(self.c.execute(sql_validated, (id,)).fetchone()[0])

    def validate_track(self, id, download_url=None):
        if download_url:
            sql_download_url = """
                UPDATE tracks
                SET download_url = ?
                WHERE id = ?;
            """
            self.c.execute(sql_download_url, (download_url, id))
        sql_validate = """
            UPDATE tracks
            SET validated = 1
            WHERE id = ?;
        """
        self.c.execute(sql_validate, (id,))
        self.conn.commit()


if __name__ == "__main__":
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
