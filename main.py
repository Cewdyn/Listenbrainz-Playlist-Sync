from modules.listenbrainz_functions import get_weeklyjams_playlist,get_weeklyexploration_playlist,get_dailyjams_playlist
from modules.plex_functions import set_section, missing_tracks
from modules.email_utils import send_missing_tracks_email
from datetime import date
import calendar
from modules.global_variables import cfg

from modules.logger_utils import logger


if __name__ == "__main__":
    my_date = date.today()
    today = calendar.day_name[my_date.weekday()]
    # logger.info("today is "+today)

    set_section()
    if cfg['create_daily']:
        try:
            get_dailyjams_playlist(cfg['user_token'])
        except Exception:
            pass
    # if today == "Monday" and cfg['create_weekly']:
    if cfg['create_weekly']:
        try:
            get_weeklyjams_playlist(cfg['user_token'])
        except Exception:
            pass
        try:
            get_weeklyexploration_playlist(cfg['user_token'])
        except Exception:
            pass 
    send_missing_tracks_email(missing_tracks)

#get_weeklyexploration_playlist(cfg['user_token'])
