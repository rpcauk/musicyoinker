import sqlite3


def initialise_db(db_name):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(
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
    c.execute(
        """
            CREATE TABLE IF NOT EXISTS albums (
                id text PRIMARY KEY,
                title text NOT NULL,
                date text,
                total_tracks text,
                artwork_url text NOT NULL,
                explicit boolean NOT NULL DEFAULT 0
            )
        """
    )
    c.execute(
        """
            CREATE TABLE IF NOT EXISTS artists (
                id text PRIMARY KEY,
                name text NOT NULL,
                artwork_url text NOT NULL
            )
        """
    )
    c.execute(
        """
            CREATE TABLE IF NOT EXISTS  playlists (
                id text PRIMARY KEY,
                name text NOT NULL,
                owner text,
                artwork_url text NOT NULL
            )
        """
    )
    c.execute(
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
    c.execute(
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
    c.execute(
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
    c.execute(
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
    conn.commit()
    conn.close()
