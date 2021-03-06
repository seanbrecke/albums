import sys
import os
import re
import gc
import logging
from datetime import datetime
from typing import List, Any, Optional, Dict

import httplib2  # type: ignore[import]
import xlrd  # type: ignore[import]
import yaml
import git  # type: ignore[import]
from googleapiclient import discovery  # type: ignore[import]
from flask import Flask, jsonify, request
from waitress import serve

this_dir = os.path.dirname(__file__)
root_dir = os.path.join(this_dir, os.pardir)
sys.path.insert(0, root_dir)

from nextalbums import SETTINGS
from nextalbums.core_gsheets import get_credentials
from nextalbums.create_sql_statements import sql_datafile
from nextalbums.export import split_comma_separated

app = Flask(__name__)

logging.basicConfig()
logger = logging.getLogger("waitress")
logger.setLevel(logging.INFO)

cache_file = sql_datafile("score_artist_cache.yaml")


class FileCache:
    def __init__(self, filename):
        self.filename = filename
        self.data = None
        self.read_at = None

    def read(self):
        with open(self.filename) as data:
            self.data = yaml.load(data, Loader=yaml.FullLoader)
        self.read_at = int(os.path.getmtime(self.filename))

    def get(self):
        if self.read_at != int(os.path.getmtime(self.filename)):
            self.read()
        return self.data


artist_cache: FileCache = FileCache(cache_file)


def make_request() -> List[List[Any]]:
    """
    crude way of keeping this up to date -- Re-create the credential/service
    each time a request is made, so that the credentials are valid

    returns the results array of arrays
    """
    http = get_credentials().authorize(httplib2.Http())
    discoveryUrl = "https://sheets.googleapis.com/$discovery/rest?version=v4"
    service = discovery.build(
        "sheets",
        "v4",
        http=http,
        discoveryServiceUrl=discoveryUrl,
        cache_discovery=False,
    )
    data: List[List[Any]] = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=SETTINGS.SPREADSHEET_ID,
            range="Music!A1:L",
            valueRenderOption="FORMULA",
        )
        .execute()
        .get("values", [])
    )
    return data


class album:

    attrs = [
        "score",
        "album_name",
        "cover_artist",
        "listened_str",
        "album_artwork",
        "discogs_url",
        "reasons",
        "genres",
        "styles",
        "main_artists",
        "other_artists",
    ]

    def __init__(self, vals: List):

        #  add empty rows to places where spreadsheet had no values
        while len(vals) < 12:
            vals.append("")
        (
            score,
            album_name,
            artists_on_album_cover,
            year,
            date,
            reasons,
            album_artwork,
            discogs_url,
            main_artists,
            genres,
            styles,
            credits,
        ) = map(str, vals)
        try:
            self.score: Optional[float] = float(score)
        except ValueError:  # could be empty or 'can't find'
            self.score = None
        self.album_name = album_name
        self.cover_artist = artists_on_album_cover
        self.year = int(year)
        if date.strip():
            if self.score is None:
                print(
                    "WARNING: {} ({}) has no 'score' but has a 'listened on' date".format(
                        self.album_name, self.cover_artist
                    )
                )
            self.listened_on = xlrd.xldate_as_datetime(int(date), 0)
            self.listened_str = self.listened_on.strftime("%Y-%m-%d")
        else:
            if self.score is not None:
                print(
                    "WARNING: {} ({}) has no 'listened on' date but has a 'score'".format(
                        self.album_name, self.cover_artist
                    )
                )
            self.listened_on = None
            self.listened_str = None
        artwork = re.search(r"https?://[^\"]+", album_artwork)
        if artwork:
            self.album_artwork: Optional[str] = artwork.group(0)
        else:
            self.album_artwork = None
            print(
                "Warning. No Album Artwork extracted from '{}' for '{}'".format(
                    album_artwork, album_name
                )
            )
        self.discogs_url = discogs_url if discogs_url.strip() else None

        self.reasons = split_comma_separated(reasons)
        self.genres = split_comma_separated(genres)
        self.styles = split_comma_separated(styles)

        self.main_artists = []
        for main_id in main_artists.strip().split("|"):
            if main_id.strip():
                self.main_artists.append(int(main_id.strip()))

        self.other_artists = []
        for other_id in credits.strip().split("|"):
            if other_id.strip():
                self.other_artists.append(int(other_id.strip()))

    def __repr__(self) -> str:
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(
                [
                    "{}={}".format(attr, repr(getattr(self, attr)))
                    for attr in self.__class__.attrs
                ]
            ),
        )

    __str__ = __repr__

    def to_dict(self) -> Dict[str, Any]:
        return {attr: getattr(self, attr) for attr in self.__class__.attrs}


def request_albums() -> List[album]:
    resp = make_request()
    if resp:
        return [album(a) for a in resp[1:]]
    else:
        return []


# route to get albums I've listened to with different filters
# all are optional, see defaults below
# limit=int
# orderby=score|listened_on
# sort=asc|desc
@app.route("/")
def album_route():

    gc.collect()

    logger.info(
        "{} '/' {}".format(
            datetime.now().strftime("%d-%b-%Y %H:%M:%S.%f"), dict(request.args)
        )
    )

    # parse request args
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    sort_by = request.args.get("orderby", "score")
    order = request.args.get("sort", "desc")
    if sort_by not in ["score", "listened_on"]:
        return jsonify({"error": f"{sort_by} not in 'score', 'listened_on'"}), 400
    if order not in ["asc", "desc"]:
        return jsonify({"error": f"{order} not in 'asc', 'desc'"}), 400

    # request albums from google api
    albums = request_albums()

    # sort according to flags passed
    albums = list(filter(lambda o: o.score is not None, albums))
    sort_order: bool = order != "asc"
    if sort_by == "score":
        albums.sort(key=lambda o: o.score, reverse=sort_order)
    else:
        albums.sort(key=lambda o: o.listened_on, reverse=sort_order)

    return jsonify([a.to_dict() for a in albums[:limit]])


# route to get names for discord artist IDs
# expects get data like: /arists?ids=40,2042,234
@app.route("/artists")
def artist_names():

    gc.collect()

    logger.info(
        "{} '/' {}".format(
            datetime.now().strftime("%d-%b-%Y %H:%M:%S.%f"), dict(request.args)
        )
    )

    # update git repo
    g = git.cmd.Git(root_dir)
    g.pull()
    # get cache file information
    acache = artist_cache.get()
    # parse ids from GET arg
    requested_ids = map(int, request.args["ids"].split(","))
    # respond with names
    return jsonify({aid: acache.get(aid) for aid in requested_ids})


if __name__ == "__main__":
    # since this isn't hosted on the public internet
    # and is only going to be used by other
    # applications on the server, to query information,
    # this uses waitress instead of something more complex
    serve(app, host="0.0.0.0", port=os.environ.get("ALBUM_PORT", 8083))
