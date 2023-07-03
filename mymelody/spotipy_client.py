import sys
from typing import List, Optional
from spotipy import Spotify, SpotifyOAuth
import os
from mymelody.database_connection import Singleton


class SpotipyClient(metaclass=Singleton):
    def __init__(
        self,
        scope: List[str],
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        sc_params = {}

        if not scope:
            print(f"No scopes specified!")
            sys.exit(1)
        sc_params["scope"] = scope
        sc_params["open_browser"] = False

        client_ids = (client_id, os.getenv("SPOTIPY_CLIENT_ID"))
        client_ids = [x for x in client_ids if x is not None]
        if client_ids:
            sc_params["client_id"] = client_ids[0]

        client_secrets = (client_secret, os.getenv("SPOTIPY_CLIENT_SECRET"))
        client_secrets = [x for x in client_secrets if x is not None]
        if client_ids:
            sc_params["client_secret"] = client_secrets[0]

        if not redirect_uri:
            redirect_uri = "https://localhost:8888/callback"
        redirect_uris = (redirect_uri, os.getenv("SPOTIPY_REDIRECT_URI"))
        redirect_uris = [x for x in redirect_uris if x is not None]
        if client_ids:
            sc_params["redirect_uri"] = redirect_uris[0]

        if len(sc_params) != 5:
            print("Environment variables not set!")
            if os.name == "nt":
                print('  $env:SPOTIPY_CLIENT_ID="<value>"')
                print('  $env:SPOTIPY_CLIENT_SECRET="<value>"')
            else:
                print('  export SPOTIPY_CLIENT_ID="<value>"')
                print('  export SPOTIPY_CLIENT_SECRET="<value>"')
            sys.exit(1)

        spotipy_client = Spotify(auth_manager=SpotifyOAuth(**sc_params))
        return spotipy_client


def create_client(
    scope: List[str],
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> Spotify:
    sc_params = {}

    if not scope:
        print(f"No scopes specified!")
        sys.exit(1)
    sc_params["scope"] = scope
    sc_params["open_browser"] = False

    client_ids = (client_id, os.getenv("SPOTIPY_CLIENT_ID"))
    client_ids = [x for x in client_ids if x is not None]
    if client_ids:
        sc_params["client_id"] = client_ids[0]

    client_secrets = (client_secret, os.getenv("SPOTIPY_CLIENT_SECRET"))
    client_secrets = [x for x in client_secrets if x is not None]
    if client_ids:
        sc_params["client_secret"] = client_secrets[0]

    if not redirect_uri:
        redirect_uri = "https://localhost:8888/callback"
    redirect_uris = (redirect_uri, os.getenv("SPOTIPY_REDIRECT_URI"))
    redirect_uris = [x for x in redirect_uris if x is not None]
    if client_ids:
        sc_params["redirect_uri"] = redirect_uris[0]

    if len(sc_params) != 5:
        print("Environment variables not set!")
        if os.name == "nt":
            print('  $env:SPOTIPY_CLIENT_ID="<value>"')
            print('  $env:SPOTIPY_CLIENT_SECRET="<value>"')
        else:
            print('  export SPOTIPY_CLIENT_ID="<value>"')
            print('  export SPOTIPY_CLIENT_SECRET="<value>"')
        sys.exit(1)

    spotipy_client = Spotify(auth_manager=SpotifyOAuth(**sc_params))
    return spotipy_client
