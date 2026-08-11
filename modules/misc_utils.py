import difflib
import re
from datetime import datetime, timedelta

def get_playlist_daily_title(username: str):
    """
    Gets the date of the most recent Monday and formats it for the title to search for
    :param username: The username for the playlist
    :return: The formatted title to search for
    """
    # Get the current date
    current_date = datetime.now()

    # Calculate the difference in days between the current day and Monday (weekday 0)
    days_to_monday = (current_date.weekday() - 0) % 7

    # Subtract the difference to get the date of the most recent Monday
    most_recent_monday = current_date - timedelta(days=days_to_monday)

    # Format the date as 'YYYY-MM-DD'
    formatted_date = most_recent_monday.strftime('%Y-%m-%d')

    title = f"Daily Jams for {username}"

    return title

def get_playlist_title(username: str):
    """
    Gets the date of the most recent Monday and formats it for the title to search for
    :param username: The username for the playlist
    :return: The formatted title to search for
    """
    # Get the current date
    current_date = datetime.now()

    # Calculate the difference in days between the current day and Monday (weekday 0)
    days_to_monday = (current_date.weekday() - 0) % 7

    # Subtract the difference to get the date of the most recent Monday
    most_recent_monday = current_date - timedelta(days=days_to_monday)

    # Format the date as 'YYYY-MM-DD'
    formatted_date = most_recent_monday.strftime('%Y-%m-%d')

    title = f"Weekly Jams for {username}"

    return title

def get_playlist_exploration_title(username: str):
    """
    Gets the date of the most recent Monday and formats it for the title to search for
    :param username: The username for the playlist
    :return: The formatted title to search for
    """
    # Get the current date
    current_date = datetime.now()

    # Calculate the difference in days between the current day and Monday (weekday 0)
    days_to_monday = (current_date.weekday() - 0) % 7

    # Subtract the difference to get the date of the most recent Monday
    most_recent_monday = current_date - timedelta(days=days_to_monday)

    # Format the date as 'YYYY-MM-DD'
    formatted_date = most_recent_monday.strftime('%Y-%m-%d')

    title = f"Weekly Exploration for {username}"

    return title

def normalize_characters(title: str):
    """
    Swaps certain mapped characters in a title in order to get a better match
    :param title: The original track title
    :return: The normalized title
    """
    char_mapping = {
        '...': chr(8230),
        '“': '"',
        '”': '"',
        '’': "'",
        '‐': '-',
    }

    for key, value in char_mapping.items():
        title = title.replace(key, value)

    return title


def normalize_artist(name: str) -> str:
    """
    Normalizes an artist name for comparison purposes (lowercase, strips
    featured-artist noise and punctuation).
    :param name: The artist name to normalize
    :return: The normalized artist name
    """
    if not name:
        return ""

    name = name.lower()
    # Drop "feat./ft./featuring ..." suffixes so collabs still match the primary artist
    name = re.split(r'\bfeat\.?\b|\bft\.?\b|\bfeaturing\b', name)[0]
    # Collapse everything that isn't alphanumeric (spacing, "&" vs "and", punctuation, etc.)
    name = re.sub(r'[^a-z0-9]+', ' ', name)

    return name.strip()


def artists_match(candidate_artist: str, track_artist: str, album_artist: str, threshold: float = 0.85) -> bool:
    """
    Determines whether a Plex track's artist reasonably matches the artist(s) reported by ListenBrainz.
    Used to avoid matching a track to a same/similarly-titled song by a completely different artist.
    :param candidate_artist: The artist name of the Plex search result
    :param track_artist: The track artist reported by ListenBrainz
    :param album_artist: The album artist reported by ListenBrainz
    :param threshold: Minimum similarity ratio (0-1) to consider a fuzzy match
    :return: True if the candidate artist is a reasonable match for either expected artist
    """
    candidate_norm = normalize_artist(candidate_artist)
    if not candidate_norm:
        return False

    for expected in (track_artist, album_artist):
        expected_norm = normalize_artist(expected)
        if not expected_norm:
            continue

        if candidate_norm == expected_norm:
            return True

        # Handle cases like "Artist" matching "Artist & Other Artist" or vice versa
        if candidate_norm in expected_norm or expected_norm in candidate_norm:
            return True

        if difflib.SequenceMatcher(None, candidate_norm, expected_norm).ratio() >= threshold:
            return True

    return False
