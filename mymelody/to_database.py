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
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

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
            self.c.execute(sql, list(album_data.values()))
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
            artist_data = self.spotipy_client.artist(artist["id"])
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
    # Manual Add                                                               #
    ############################################################################
    def manual_add_track(self, id, data):
        track = self.get_track(id)
        if track:
            raise Exception(f"Track {dict(track)['title']} already exists [id: {id}]")
        album = data.pop("album")
        artists = data.pop("artists")
        track_sql = """
            INSERT INTO tracks (
                id,
                title,
                length,
                date,
                discnumber,
                tracknumber,
                download_url,
                artwork_url,
                explicit,
                validated
            ) 
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.c.execute(track_sql, list(data.values()))
        self.conn.commit()

        album_tracks_sql = """
            INSERT INTO album_tracks (
                track_id,
                album_id
            )
            VALUES(?, ?)
        """
        self.c.execute(album_tracks_sql, (id, album))
        self.conn.commit()

        for artist in artists:
            # Add link between track and artists
            track_artists_sql = """
                INSERT INTO track_artists (
                    track_id,
                    artist_id
                )
                VALUES(?,?)
            """
            self.c.execute(track_artists_sql, (id, artist))
            self.conn.commit()
        return self.get_track(id)

    def manual_add_album(self, id, data):
        album = self.get_album(id)
        if album:
            raise Exception(f"Album {dict(album)['title']} already exists [id: {id}]")
        artists = data.pop("artists")
        album_sql = """
            INSERT INTO albums (
                id,
                title,
                date,
                total_tracks,
                artwork_url,
                explicit
            ) 
            VALUES(?, ?, ?, ?, ?, ?)
        """
        self.c.execute(album_sql, list(data.values()))
        self.conn.commit()
        for artist in artists:
            album_artists_sql = """
                INSERT OR IGNORE INTO album_artists (
                    album_id,
                    artist_id
                )
                VALUES(?,?)
            """
            self.c.execute(album_artists_sql, (id, artist))
            self.conn.commit()
        return self.get_album(id)

    def manual_add_artist(self, id, data):
        artist = self.get_artist(id)
        if artist:
            raise Exception(f"Artist {dict(artist)['name']} already exists [id: {id}]")
        artist_sql = """
            INSERT INTO albums (
                id,
                name,
                artwork_url
            ) 
            VALUES(?, ?, ?)
        """
        self.c.execute(artist, list(data.values()))
        self.conn.commit()

    ############################################################################
    # Collect                                                                  #
    ############################################################################
    def collect_track(self, id):
        track = self.get_track(id)
        if track is None:
            return self.add_track(id)
        return track

    def collect_album(self, id):
        album = self.get_album(id)
        if album is not None:
            if album["total_tracks"] == len(album["tracks"]):
                return album
        album_tracks = [
            str(track["id"]) for track in self.spotipy_client.album_tracks(id)["items"]
        ]
        for track_id in album_tracks:
            self.collect_track(track_id)
        return self.get_album(id)

    def collect_artist(self, id):
        album_ids = []
        for album_type in ("album", "single", "compilation"):
            album_type_ids = []
            while True:
                results = [
                    str(album["id"])
                    for album in self.spotipy_client.artist_albums(
                        id,
                        limit=20,
                        offset=len(album_type_ids),
                        album_type=album_type,
                    )["items"]
                ]
                album_type_ids += results
                if len(results) != 20:
                    break
            album_ids += album_type_ids

        for album_id in album_ids:
            self.collect_album(album_id)
        return self.get_artist(id)

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

    def get_album(self, id):
        album = self.c.execute("SELECT * FROM albums WHERE id = ?", (id,)).fetchone()
        if album:
            album = dict(album)
            album["artists"] = self.get_album_artists(id)
            album["tracks"] = self.get_album_tracks(id)
            return album

    def get_artist(self, id):
        artist = self.c.execute("SELECT * FROM artists WHERE id = ?", (id,)).fetchone()
        if artist:
            artist = dict(artist)
            artist["albums"] = self.get_artist_albums(id)
            artist["tracks"] = self.get_artist_tracks(id)
            return artist

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
            SELECT tracks.id, tracks.title
            FROM track_artists
            JOIN tracks
            ON track_artists.track_id = tracks.id
            WHERE track_artists.artist_id = ?
        """

        return [dict(track) for track in self.c.execute(sql, (id,)).fetchall()]

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
            SELECT tracks.id, tracks.title
            FROM album_tracks
            JOIN tracks
            ON album_tracks.track_id = tracks.id
            WHERE album_tracks.album_id = ?
        """
        return [dict(row) for row in self.c.execute(sql, (id,)).fetchall()]

    def get_artist_albums(self, id):
        sql = """
            SELECT albums.id, albums.title 
            FROM album_artists
            JOIN albums
            ON album_artists.album_id = albums.id
            WHERE album_artists.artist_id = ?
        """
        return [dict(row) for row in self.c.execute(sql, (id,)).fetchall()]

    def get_track_album(self, id):
        sql = """
            SELECT albums.id, albums.title
            FROM album_tracks
            JOIN albums
            ON album_tracks.album_id = albums.id
            WHERE album_tracks.track_id = ?
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

    ############################################################################
    # Update                                                                   #
    ############################################################################

    def update_track(self, id, values):
        if "album" in values:
            album = values.pop("album")
            if album is not None:
                self.c.execute(
                    f"UPDATE album_tracks SET album_id = ? WHERE track_id = ?",
                    (album, id),
                )
                self.conn.commit()
        if "artists" in values:
            artists = values.pop("artists")
            if artists is not None:
                for artist in artists:
                    self.c.execute(
                        f"UPDATE track_artists SET artist_id = ? WHERE track_id = ?",
                        (artist, id),
                    )
                self.conn.commit()
        if "hidden" in values:
            hidden = values.pop("hidden")
            if hidden is not None:
                self.c.execute(
                    f"UPDATE tracks SET hidden = ? WHERE id = ?",
                    (int(hidden), id),
                )
                self.conn.commit()
        for k, v in values.items():
            if v is None:
                continue
            self.c.execute(f"UPDATE tracks SET {k} = ? WHERE id = ?", (v, id))
            self.conn.commit()
        return self.get_track(id)

    def update_album(self, id, values):
        if "hidden" in values:
            hidden = values.pop("hidden")
            if hidden is not None:
                for track in self.get_album_tracks(id):
                    self.update_track(track["id"], {"hidden": int(hidden)})
        if "artwork_url" in values:
            artwork_url = values.pop("artwork_url")
            for track in self.get_album_tracks(id):
                self.update_track(track["id"], {"artwork_url": artwork_url})
        for k, v in values.items():
            if v is None:
                continue
            self.c.execute(f"UPDATE albums SET {k} = ? WHERE id = ?", (v, id))
            self.conn.commit()
        return self.get_album(id)

    def update_artist(self, id, values):
        for k, v in values.items():
            if v is None:
                continue
            self.c.execute(f"UPDATE artists SET {k} = ? WHERE id = ?", (v, id))
            self.conn.commit()
        return self.get_album(id)

    ############################################################################
    # Delte                                                                    #
    ############################################################################

    def delete_track(self, id):
        track = self.get_track(id)
        if track:
            self.c.execute("DELETE FROM tracks WHERE id = ?", (id,))
            self.c.execute("DELETE FROM album_tracks WHERE track_id = ?", (id,))
            self.c.execute("DELETE FROM track_artists WHERE track_id = ?", (id,))
            self.conn.commit()
            print(f"Track {track['title']} [{id}] deleted successfullly")
        else:
            raise Exception(f"Could not find Track with ID {id}")

    def delete_album(self, id):
        album = self.get_album(id)
        if album:
            for track in album["tracks"]:
                self.delete_track(track["id"])
            self.c.execute("DELETE FROM albums WHERE id = ?", (id,))
            self.c.execute("DELETE FROM album_artists WHERE album_id = ?", (id,))
            self.conn.commit()
            print(f"Album {album['title']} [{id}] deleted successfullly")


if __name__ == "__main__":
    mmdb = MyMelodyDatabase(create_client(["user-library-read"]))
