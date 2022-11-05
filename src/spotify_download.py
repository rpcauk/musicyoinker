import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import List
import os
import sys


class SpotifyDownload:
    def __init__(
        self,
        scope,
        spotipy_client_id=None,
        spotipy_client_secret=None,
        spotipy_redirect_uri=None,
    ) -> None:
        self._spotipy_client = self._create_spotipy_client(
            scope=scope,
            spotipy_client_id=spotipy_client_id,
            spotipy_client_secret=spotipy_client_secret,
            spotipy_redirect_uri=spotipy_redirect_uri,
        )
        self._config = {"tracks": {}, "artwork": {}}

    def _create_spotipy_client(
        self,
        scope: List[str],
        spotipy_client_id=None,
        spotipy_client_secret=None,
        spotipy_redirect_uri=None,
    ):
        sc_params = {}

        if not scope:
            print(f"No scopes specified, check the link below for possible options")
            print(
                f"https://developer.spotify.com/documentation/general/guides/authorization/scopes/"
            )
            sys.exit(1)
        sc_params["scope"] = scope

        required_values = True
        if not os.getenv("SPOTIPY_CLIENT_ID") and not spotipy_client_id:
            print(f"[SPOTIPY_CLIENT_ID] value not found!")
            print(f"Either set the environment variable")
            print(f"Or override with a parameter value")
            required_values = required_values and False
        elif spotipy_client_id:
            print(f"Overriding [SPOTIPY_CLIENT_ID] value from parameter")
            sc_params["client_id"] = spotipy_client_id
        elif os.getenv("SPOTIPY_CLIENT_ID"):
            print(f"Using [SPOTIPY_CLIENT_ID] from environment variable")
            sc_params["client_id"] = os.getenv("SPOTIPY_CLIENT_ID")
        print()

        if not os.getenv("SPOTIPY_CLIENT_SECRET") and not spotipy_client_id:
            print(f"[SPOTIPY_CLIENT_SECRET] value not found!")
            print(f"Either set the environment variable")
            print(f"Or override with a parameter value")
            required_values = required_values and False
        elif spotipy_client_id:
            print(f"Overriding [SPOTIPY_CLIENT_SECRET] value from parameter")
            sc_params["client_secret"] = spotipy_client_secret
        elif os.getenv("SPOTIPY_CLIENT_SECRET"):
            print(f"Using [SPOTIPY_CLIENT_SECRET] from environment variable")
            sc_params["client_secret"] = os.getenv("SPOTIPY_CLIENT_SECRET")
        print()

        if not required_values:
            sys.exit(1)

        default_redirect = "https://localhost:8888/callback"
        if not os.getenv("SPOTIPY_REDIRECT_URI") and not spotipy_redirect_uri:
            print(f"[SPOTIPY_REDIRECT_URI] value not found!")
            print(f"Either set the environment variable")
            print(f"Or override with a parameter value")
            print(f"Using default value [{default_redirect}]")
            sc_params["redirect_uri"] = default_redirect
        elif spotipy_redirect_uri:
            print(f"Overriding [SPOTIPY_REDIRECT_URI] value from parameter")
            sc_params["redirect_uri"] = spotipy_redirect_uri
        elif os.getenv("SPOTIPY_REDIRECT_URI"):
            print(f"Using [SPOTIPY_REDIRECT_URI] from environment variable")
            sc_params["redirect_uri"] = os.getenv("SPOTIPY_REDIRECT_URI")
        print()

        spotipy_client = spotipy.Spotify(auth_manager=SpotifyOAuth(**sc_params))
        return spotipy_client
