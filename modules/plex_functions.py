import plexapi.exceptions
import plexapi
import uuid
import os

from plexapi.server import PlexServer

import modules.global_variables as g
from modules.logger_utils import logger
from modules.misc_utils import *

# Persistent UUID for Plex device identification
uuid_file = os.path.join(g.config_dir, "UUID")

uuid_num = None
if os.path.exists(uuid_file):
    with open(uuid_file) as handle:
        for line in handle.readlines():
            line = line.strip()
            if len(line) > 0:
                uuid_num = line
                break
if not uuid_num:
    uuid_num = uuid.uuid4()
    try:
        with open(uuid_file, "w") as handle:
            handle.write(str(uuid_num))
        logger.info(f"UUID file created: {uuid_file}")
    except Exception as e:
        logger.error(f"Failed to create UUID file: {e}")

plexapi.BASE_HEADERS["X-Plex-Client-Identifier"] = str(uuid_num)

if g.cfg['baseurl'] == "" or g.cfg['token'] == "":
    raise ValueError("Plex base URL and token cannot be blank.")

plex = PlexServer(g.cfg['baseurl'], g.cfg['token'])

plex_tracks = []  # Found tracks to be added to Plex
missing_tracks = []  # Any tracks that aren't found in Plex

playlist_prefix = g.cfg['playlist_prefix']

from datetime import date
import calendar
my_date = date.today()
today = calendar.day_name[my_date.weekday()]
#print(today)

def set_section():
    """
    Sets the Plex library section to search in
    """
    # Handle if the section name passed in is blank
    if g.cfg['music_section'] == "":
        # Throw an error
        raise ValueError("Section name cannot be blank.")

    # Set the section
    try:
        g.section = plex.library.section(g.cfg['music_section'])
    except plexapi.exceptions.NotFound:
        raise ValueError("Section not found.")


def filter_words_from_title(input_title):
    """
    Filters out tracks with certain words in the title before searching for them in Plex.
    :return:
    """
    title = input_title
    filter_words = g.cfg.get('filter_words',[])
    for word in filter_words:
        if word in input_title:
            # Remove word from title and update track title
            title = input_title.replace(word, '')
            # Remove empty parentheses from title and update track title
            title = title.replace('()', '')

    return title


# Search through the Plex library for the track matching the name
def search_for_track(track_list: list[dict]):
    """
    Search through the Plex library for the track matching the names in the track_list.
    Plex's title search is loose (it will happily return same/similarly-titled tracks by a
    completely different artist), so every candidate is verified against the ListenBrainz
    artist/album artist (or MusicBrainz GUID, when available) before being accepted.
    :param track_list: List of tracks to search for
    """

    count = 0

    for track in track_list:
        title = track['title']
        artist = track['artist']
        album_artist = track['album_artist']
        mbids = track['mbids'] or []

        try:
            logger.info(f"Searching for {title} by {artist}...")

            search_result = []
            for variant in generate_title_search_variants(title):
                search_result = g.section.searchTracks(title=variant)
                if search_result:
                    break

            if not search_result:
                # Attempt normalizing/filtering the title and search again with those variants too
                logger.warning("No match on first pass, attempting to normalize title...")
                normalized_title = normalize_characters(title)
                filtered_title = filter_words_from_title(normalized_title)
                for variant in generate_title_search_variants(filtered_title):
                    search_result = g.section.searchTracks(title=variant)
                    if search_result:
                        break

            if not search_result:
                logger.error(f"No match found for {title} by {artist}, skipping...")
                missing_tracks.append(track)
                continue

            if len(search_result) > 1:
                logger.warning(f"Found {len(search_result)} results for {title}, checking for a matching artist...")

            match = None

            # Prefer an exact MusicBrainz recording match, when we have MBIDs to compare against
            for result in search_result:
                if result.guids and any(guid.id in mbids for guid in result.guids):
                    logger.info(f"Found {result.title} - {result.artist().title} with GUID Matching")
                    match = result
                    break

            # Fall back to a fuzzy artist match so a same-titled track by a different artist isn't picked
            if not match:
                for result in search_result:
                    result_artist = result.artist().title
                    if artists_match(result_artist, artist, album_artist):
                        logger.info(f"Found {result.title} - {result_artist} with Artist Matching")
                        match = result
                        break

            if match:
                count += 1
                plex_tracks.append(match)
            else:
                logger.error(f"Found {len(search_result)} result(s) for {title}, but none matched artist "
                             f"'{artist}' / '{album_artist}', skipping...")
                missing_tracks.append(track)

        except plexapi.exceptions.NotFound:
            raise ValueError("Track not found.")

    logger.info(f"Found a total of {count} tracks")
    logger.warning(f"Missing {len(missing_tracks)} tracks: ")
    for track in missing_tracks:
        logger.warning(track['title'])

    create_playlist()


def create_playlist():
    """
    Creates a playlist in Plex. Will check if a playlist with the same name exists, and if it does it will
    replace/add tracks as needed
    """

    filter_tracks()

    logger.info("Checking playlist status...")
    playlistname = playlist_prefix+g.playlist_name
    if g.playlist_name == "Daily Jams":
        poster = g.cfg['daily_poster']
    elif g.playlist_name == "Weekly Exploration":
        poster = g.cfg['weekly_exploration_poster']
    else:
        poster = g.cfg['weekly_jam_poster']
    logger.error("==============================================================================================") 

    #exit()
    #playlist = g.section.createPlaylist(title=playlist_prefix+g.playlist_name, items=plex_tracks)


    try:
        # Check if the playlist already exists
        # playlist = g.section.playlist(playlist_prefix+g.playlist_name+"_"+today)

        playlist = g.section.playlist(playlistname)
        #playlist = g.section.playlist(playlist_prefix+g.playlist_name+"_"+today)
        logger.warning("Playlist already exists, checking for new tracks...")

        if playlist.items() == plex_tracks:
            logger.error("No new tracks found, skipping creation")
            return

        # Remove old tracks
        logger.info("New tracks found, updating playlist...")
        items = playlist.items()
        playlist.removeItems(items)
        logger.info("Old tracks removed from playlist")

        # Add new tracks
        playlist.addItems(plex_tracks)
        logger.info("Tracks added to playlist")

    except plexapi.exceptions.NotFound:
        try:
            logger.info("Playlist not found, creating...")
            playlist = g.section.createPlaylist(title=playlistname, items=plex_tracks)
            #playlist = g.section.createPlaylist(title=playlist_prefix+g.playlist_name, items=plex_tracks)
            if poster != 'YOUR_FILE_PATH':
                playlist.uploadPoster(filepath=poster)
            playlist.editSummary(summary=g.playlist_summary)
            logger.info("Playlist created")
        except Exception as e:
            # Handle specific exception for playlist creation failure
            logger.error(f"Failed to create playlist: {e}")
            # Add additional actions or logging if needed
    except Exception as e:
        # Handle other specific exceptions if needed
        logger.error(f"An unexpected error occurred: {e}")


def filter_tracks():
    """
    Filters out tracks by genre before creating/modifying the playlist.
    :return:
    """
    filter_genre = g.cfg.get('filter_genre','YOUR_GENRE')
    if filter_genre != 'YOUR_GENRE':
        for item in plex_tracks[:]:  # Iterate over a copy
            track_album = item.album()
            genres = track_album.genres
            for album_genre in genres:
                if album_genre.tag == filter_genre:
                    logger.info(f'Track "{item.title}" removed due to genre filter.')
                    plex_tracks.remove(item)  # Safe removal
                    break  # Exit inner loop once removed

