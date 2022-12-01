# -*- coding: utf-8 -*-
# This file is part of everylotbot
# Copyright 2016 Neil Freeman
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import datetime
import logging
import pytz
import twitter_bot_utils as tbu

from . import __version__ as version
from .everylot import EveryLot
from .mastodon import mastodon_instance, mastodon_image, send_toot

def badtime(hoursbetween=1, quiethours=None, timezone='US/Eastern', logger=None):
    """
    Some schedulers (like Pythonanywhere's) only give you the choice between
    hourly or daily.  This allows us to filter the hour.  It's a bad time if
    it's been less than hoursbetween, or if it's during quiethours
    """
    now = datetime.datetime.now(pytz.timezone(timezone))
    logger.debug("The hour is: {}".format(now.hour))

    if hoursbetween and now.hour % hoursbetween > 0:
        return True
    if quiethours and now.hour >= quiethours[0]:
        return True
    if quiethours and now.hour < quiethours[1]:
        return True

    return False

def main():
    parser = argparse.ArgumentParser(description='every lot twitter bot')
    parser.add_argument('user', type=str)
    parser.add_argument('database', type=str)
    parser.add_argument('--id', type=str, default=None)
    parser.add_argument('-s', '--search-format', type=str, default=None,
                        help='Python format string use for searching Google')
    parser.add_argument('-p', '--print-format', type=str, default=None,
                        help='Python format string use for poster to Twitter')
    parser.add_argument('-nq', '--no-quiet', action='store_true')

    tbu.args.add_default_args(parser, version=version, include=('config', 'dry-run', 'verbose', 'quiet'))

    args = parser.parse_args()
    api = tbu.api.API(args)

    logger = logging.getLogger(args.user)
    logger.debug('everylot starting with %s, %s', args.user, args.database)

    if (not args.no_quiet and \
        ('hoursbetween' in api.config or 'quiethours' in api.config)) \
        and badtime(
            api.config['hoursbetween'],
            api.config['quiethours'],
            api.config.get('timezone', None),
            logger
            ):
        logger.debug(
            "It's a bad time for tweeting (hoursbetween={}, quiet={})".format(
                api.config['hoursbetween'],
                api.config['quiethours']
                )
            )
        exit(0)

    el = EveryLot(args.database,
                  logger=logger,
                  print_format=args.print_format,
                  search_format=args.search_format,
                  id_=args.id,
                  phrasefile=api.config.get('phrasefile'))

    if not el.lot:
        logger.error('No lot found')
        return

    # get the streetview image and upload it
    image = el.get_streetview_image(api.config['streetview'])

    if not args.dry_run:
        mastodon = mastodon_instance(api.config['mastodon'])
        mastodon_media_id = mastodon_image(mastodon, image)

        media = api.media_upload('sv.jpg', file=image)

        # compose an update with all the good parameters
        # including the media string.
        update = el.compose(media.media_id_string)
        logger.info(update['status'])

        logger.debug("posting")
        api.update_status(**update)

        send_toot(mastodon, update['status'], mastodon_media_id)
        el.mark_as_tweeted()


if __name__ == '__main__':
    main()
