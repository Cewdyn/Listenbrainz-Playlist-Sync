import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import modules.global_variables as g
from modules.logger_utils import logger


def send_missing_tracks_email(missing_tracks: list[dict]):
    """
    Sends an email listing tracks that were not found in Plex, as an HTML table
    sorted alphabetically by artist.
    Does nothing if missing_tracks is empty or email config is incomplete.
    :param missing_tracks: list of track dicts, each with at least 'title' and 'artist'
    """
    if not missing_tracks:
        logger.info("No missing tracks, skipping email.")
        return

    email_address = g.cfg.get('email_address', '')
    email_app_password = g.cfg.get('email_app_password', '')
    email_to = g.cfg.get('email_to', '')

    if not email_address or not email_app_password or not email_to:
        logger.warning("Email config incomplete, skipping missing tracks email.")
        return

    seen = set()
    deduped_tracks = [
        t for t in missing_tracks
        if (t['artist'].lower(), t['title'].lower()) not in seen
        and not seen.add((t['artist'].lower(), t['title'].lower()))
    ]
    sorted_tracks = sorted(deduped_tracks, key=lambda t: t['artist'].lower())
    

    rows = "\n".join(
        f"<tr><td style='padding:6px 16px 6px 0;'>{track['artist']}</td>"
        f"<td style='padding:6px 0;'>{track['title']}</td></tr>"
        for track in sorted_tracks
    )

    html_body = f"""\
<html>
  <body>
    <p>The following {len(sorted_tracks)} track(s) were not found in your Plex library during this sync:</p>
    <table style="border-collapse: collapse;">
      <tr>
        <th style="text-align:left; padding:6px 16px 6px 0; border-bottom: 1px solid #ccc;">Artist</th>
        <th style="text-align:left; padding:6px 0; border-bottom: 1px solid #ccc;">Song</th>
      </tr>
      {rows}
    </table>
  </body>
</html>
"""

    msg = MIMEMultipart('alternative')
    msg['From'] = email_address
    msg['To'] = email_to
    msg['Subject'] = f"ListenBrainz Sync: {len(sorted_tracks)} tracks missing from Plex"
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_address, email_app_password)
            server.send_message(msg)
        logger.info(f"Missing tracks email sent to {email_to}.")
    except Exception as e:
        logger.error(f"Failed to send missing tracks email: {e}")
