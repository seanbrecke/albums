### albums

A collection of CSV/SQL files containing popular/acclaimed albums, used to make a inordinate list of albums to listen to.

This is a personal project of mine, but I thought I'd leave these files up here in case anyone wanted to use them. This is pretty old project and the python/generation process its pretty scattered (see `update.sh`), but the CSV/SQL files are very usable.

`python3 discogs_update.py` uses the [Discogs API](https://github.com/discogs/discogs_client) to fetch and validate the data on [the spreadsheet](https://docs.google.com/spreadsheets/d/12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M/edit#gid=1451660661).

[`spreadsheet.csv`](spreadsheet.csv); generated by [`generate_csv.py`](generate_csv.py), creates a CSV file which would allow you to create your own version of the spreadsheet, see below for installation instructions.

You can also use [`SQL/statements.sql`](SQL/) to create a MySQL schema with similar data to `spreadsheet.csv`. `spreadsheet.csv`, the files for each reason in `src` and `SQL/statements.sql`/`SQL/score_statements` will be updated whenever I add something to the list.

[`server`](./server) includes a flask server which grabs current information from spreadsheet:

```
'/' endpoint
get scored albums based on a few filters:
GET args:
limit=int, default 50
orderby=score|listened_on, default score
sort=asc|desc, defeault desc
```
```
'/artist' endpoint GET arg:
ids=id1,id2,id3,id4
(discogs artist IDs, which are returned in the response of '/')
```

#### Sources for `spreadsheet.csv`:

You can see the full list of sources for the spreadsheet in [`src`](src).

Note for '1001 Albums You Must Hear Before You Die' and 'Rolling Stone's 500 Greatest Albums of All Time', the number of albums is above 1001 and 500 respectively, as there have been multiple versions of the book, and I've included anything that was ever on the list.

[`src`](src) also contains 3 files that list albums I added [Manually](src/Manual.csv), on a [Recommendation](src/Recommendation.csv), or because of a [Relation](src/Relation.csv) (I liked an artist so I added more of their works). These albums are not listed in `spreadsheet.csv`

The format of all files in [src](src) except for [`all.csv`](src/all.csv) and [`valid_albums.csv`](src/valid_albums.csv) is:

`Album Name, Artists on Cover, Year, DiscogsURL, Genres, Styles`

`all.csv` contains albums I added manually, by relation, or on a recommendation, while `valid_albums.csv` does not. These CSV files also have a column that lists the Reason(s) the album is on the spreadsheet.

##### `nextalbums.py`

```
usage: python3 nextalbums.py [-h] [-n N] [-r] [-o] [-q] [-m]

List the Next Albums to listen to.

optional arguments:
  -h, --help    show this help message and exit
  -n N          Changes the number of albums to return. Default is 10.
  -r, --random  Chooses random albums instead of listing chronologically.
  -o, --open    Open the cell that corresponds to the next album in the
                spreadsheet online. Ignored if choosing randomly.
  -q, --quiet   quiet mode - only print errors.
  -m, --memory  Open the spreadsheet online based on the previous call to next
                albums. This is much faster since it doesn't require an API
                call (the line stored in '.prev_call')
```

###### Examples:

Return the next 7 albums to listen to (chronologically), and open the cell that corresponds to <i>September of My Years</i> in a web browser:
```
$ python3 nextalbums.py -on 7
+----------------------------+----------------+------+
| Album                      | Artist         | Year |
+----------------------------+----------------+------+
| September of My Years      | Frank Sinatra  | 1966 |
| The In Crowd               | Ramsey Lewis   | 1966 |
| The Return of Roger Miller | Roger Miller   | 1966 |
| A Man and His Music        | Frank Sinatra  | 1967 |
| Don't Come Home A-Drinkin' | Loretta Lynn   | 1967 |
| Goin' Out of My Head       | Wes Montgomery | 1967 |
| Caetano Veloso             | Caetano Veloso | 1968 |
+----------------------------+----------------+------+
```
Don't print anything and open the cell that corresponds to the next album to listen to in a web browser.
```
$ python3 nextalbums.py -qo
```

Install Dependencies: `python3 -m pip install --user --upgrade -r requirements3.txt`

#### Installation:

1. Create your own copy of the [spreadsheet](https://docs.google.com/spreadsheets/d/12htSAMg67czl8cpkj1mX0TuAFvqL_PJLI4hv1arG5-M/edit#gid=1451660661). You can open a new [google sheet](https://docs.google.com/spreadsheets/u/0/), and then File > Import [`spreadsheet.csv`](spreadsheet.csv) into a new google sheet. I'd also recommend setting a fixed row height to ensure images are all the same size (You can do this by doing Ctrl/⌘ + A repeatedly till the margins are selected, and then resizing one row to your desired height.)

2. Change the `spreadsheet_id` [here](https://gitlab.com/seanbreckenridge/albums/blob/master/nextalbums.py#L15) (the id is the long string after `/d/` in the URL when you're editing it) 

3. Edit the [pageId](https://gitlab.com/seanbreckenridge/albums/blob/master/nextalbums.py#L16) (the number after `edit#gid=` when on the google sheets URL)

4. Create a file named `client_secret.json` in the root directory which contains your credentials for a google sheets OAuth connection. [Tutorial here](https://console.developers.google.com); download your created credentials from [here](https://console.developers.google.com/apis/credentials)

5. Run `setup_credentials.py`

6. (If you want to add albums and validate them with `discogs_update.py`) Create a file `discogs_token.yaml` in the root directory (info can be found [here](https://www.discogs.com/developers/), token [here](https://www.discogs.com/settings/developers)) with contents similar to: 

```
user_agent: myPython3DiscogsClient/1.0
token: !!str FDJjksdfJkJFDNMoiweiIRWkj
```

7. If you're going to use [src/\_update_from_db.py](src/_update_from_db.py), make sure to read the [README](src/README.md) and set your MySQL credentials accordingly.
