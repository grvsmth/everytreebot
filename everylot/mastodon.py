"""
Functions for posting to Mastodon
"""
from logging import basicConfig, getLogger
from time import sleep

from mastodon import Mastodon, MastodonAPIError

basicConfig(level="DEBUG")
LOG = getLogger(__name__)

MEDIA_WAIT_TIME = 5
ATTACHMENT_ERROR = 'Impossible de joindre les fichiers en cours de traitement. Réessayez dans un instant\xa0!'


def mastodon_image(mastodon, title_image):
    mime_type = "image/png"
    media_res = mastodon.media_post(title_image, mime_type)

    if (media_res.get("type") != "image"):
        return None

    return str(media_res.get("id", None))


def send_toot(config, message, title_image):
    media_id = None

    mastodon = Mastodon(client_id = config['client_id'],
        client_secret = config['client_secret'],
        access_token = config['access_token'],
        api_base_url = config['base_uri'])

    if title_image:
        media_id = mastodon_image(mastodon, title_image)
        if media_id:
            LOG.info("media_id=" + media_id)
            # Give the server a little time to process our pic
            sleep(MEDIA_WAIT_TIME)

    try:
        status = mastodon.status_post(message, media_ids=[media_id])
    except MastodonAPIError as err:
        LOG.error("Unable to post status!  Trying without media... %s",
            err)

        if err.args[3] == ATTACHMENT_ERROR:
            mastodon.status_post(message)

    if 'id' in status:
        LOG.info("Sent toot ID# %s", status['id'])
    else:
        LOG.error(status)
