import json
import os
from random import randint
from time import sleep
from dateutil import parser
from datetime import datetime, timedelta

from twitter import Twitter as TwitterApi, OAuth, TwitterHTTPError


OAUTH_TOKEN = os.environ['OAUTH_TOKEN']
OAUTH_SECRET = os.environ['OAUTH_SECRET']
CONSUMER_KEY = os.environ['CONSUMER_KEY']
CONSUMER_SECRET = os.environ['CONSUMER_SECRET']


class Twitter(object):
    def __init__(self):
        self.t = TwitterApi(auth=OAuth(OAUTH_TOKEN, OAUTH_SECRET, CONSUMER_KEY, CONSUMER_SECRET))

    def favorites(self, count=200):
        try:
            result = self.t.favorites.list(count=count)
            return result
        except TwitterHTTPError as e:
            print "Error", e

    def favorites_destroy(self, id):
        try:
            result = self.t.favorites.destroy(_id=id)
            # import pdb;pdb.set_trace()
            print "Destroyed %s" % result['id']
            # print vars(result), dir(result)
            if result.rate_limit_remaining is not 0:
                print "rate_limit_remaining %i" % result.rate_limit_remaining
                print "rate_limit_limit %i" % result.rate_limit_limit
                print "rate_limit_reset %i" % result.rate_limit_reset
            return True
        except TwitterHTTPError as e:
            print "Error: ", e
            print vars(e)
            print dir(e)
            return None

    def favorites_create(self, tweet):
        # looks like this field is always false
        if tweet['favorited'] is True:
            print "Tweet already favorited, skipping http call"
            return None

        try:
            result = self.t.favorites.create(_id=tweet['id'])
            print "Favorited %s, %s, %s" % (result['created_at'], result['text'], result['id'])
            return result
        except TwitterHTTPError as e:
            print "Error: ", e
            print "Error Tweet: %s %s" % (tweet['id'], tweet['text'])

            error_code, error_message = get_twitter_error(e)
            # Check for update limit reached error 143
            if 143 == error_code:
                raise LimitReachedError(error_message)
            # You have already favorited this status 139
            elif 139 == error_code:
                raise AlreadyFavoritedError(error_message)
            else:
                return None

    def delete_favs(self):
        i = 0
        for f in favorites_ids(self.favorites()):
            if self.favorites_destroy(f) is not None:
                i += 1

        print "Destroyed total %i" % i

    def search_tweets(self, q, count=100, max_id=None, exclude_retweets=False, since_id=None):
        if exclude_retweets:
            q = q + '+exclude:retweets'

        # when using since_id the max_id must be an empty string or it will break and twitter will 403
        if since_id is not None and max_id is None:
            max_id = ''

        try:
            return self.t.search.tweets(q=q, result_type='recent', count=count, lang="en", max_id=max_id, since_id=since_id)
        except TwitterHTTPError as e:
            print "Error: ", e

            # Check for rate limit exceeded error 88
            error_code, error_message = get_twitter_error(e)
            if 88 == error_code:
                raise LimitReachedError(error_message)
            else:
                return None

    def search_tweets_all(self, q, count=100, exclude_retweets=True):
        tweets = []
        max_id = None

        while True:
            try:
                result = self.search_tweets(q, count, max_id, exclude_retweets)
            except (TwitterHTTPError, LimitReachedError):
                break

            for tweet in result['statuses']:
                if len(result['statuses']) is 1 and tweet['id'] == max_id:  # using max_id with no results will just return the max_id so we finish
                    break

                if tweet['id'] == max_id:  # when using a max_id the tweets are inclusive, so we skip the first
                    continue

                tweets.append(tweet)

            since_id = result['statuses'][0]['id']
            max_id = result['statuses'][-1]['id']

        return tweets


def favorites_ids(favs):
    return [f['id'] for f in favs]


def tweets_text(result):
    return [t['text'] for t in result['statuses']]


def is_older_than_days(created_at, days, compare_date=None):
    dt = parser.parse(created_at)
    dt = dt.replace(tzinfo=None)  # remove tz so we can get timedelta with now which has no tz

    #  allow the compare date to be overridden
    date_to_compare = datetime.now()
    if compare_date is not None:
        date_to_compare = compare_date

    td_created_at = date_to_compare - dt
    td_days = timedelta(days)
    return td_created_at >= td_days


class Favoriter(object):

    multiple_q = []
    twitter = Twitter()

    def __init__(self, q=None, count=1000, batch=100, multiple_q=None, delay_up_to=None, exclude_retweets=True, max_403s=5):
        if multiple_q is None:
            assert q is not None
            self.multiple_q.append(q)
        else:
            self.multiple_q = multiple_q

        self.q = q
        self.count = count
        self.batch = batch
        self.delay_up_to = delay_up_to
        self.exclude_retweets = exclude_retweets
        self.max_403s = max_403s  # how many sequential 403s to allow before stopping - a safeguard to prevent a limit reached error from twitter when looping and fav'ing already fav'd tweets

        self._reset_stats()

    def _reset_stats(self):
        self.success = 0
        self.skipped = 0
        self.fail = 0
        self.requested = 0
        self.first_id = None
        self.last_id = None
        self.sequential_403s = 0

    def search_and_fav(self, q, count=100, max_id=None):
        result = self.twitter.search_tweets(q, count, max_id, self.exclude_retweets)
        first_id = result['statuses'][0]['id']
        last_id = result['statuses'][-1]['id']

        for tweet in result['statuses']:
            if tweet['id'] == max_id:
                print "Skipping max_id %i" % max_id
                self.skipped += 1

                if len(result['statuses']) is 1:
                    raise SuccessLimitReachedError("No more results")

                continue

            if self.sequential_403s >= self.max_403s:
                raise SuccessLimitReachedError("Sequential 403 limit of %s reached" % self.max_403s)

            if self.delay_up_to is not None:
                sleep(randint(1, self.delay_up_to))

            try:
                if self.twitter.favorites_create(tweet) is not None:
                    self.success += 1
                    self.sequential_403s = 0
                else:
                    self.fail += 1
            except AlreadyFavoritedError:
                self.sequential_403s += 1
                self.fail += 1
            except LimitReachedError:
                self.fail += 1
                self.requested += 1
                raise
            finally:
                self.requested += 1

            if self.success >= self.count:
                raise SuccessLimitReachedError("Reached success limit of %i" % self.count)

        print "Favorited total %i of %i" % (self.success, len(result['statuses']))
        print "First id %s last id %s" % (first_id, last_id)
        return (first_id, last_id)

    def run(self):
        for q in self.multiple_q:
            while True:
                try:
                    self.first_id, self.last_id = self.search_and_fav(q, self.batch, self.last_id)
                except SuccessLimitReachedError as e:
                    print e
                    print vars(self)
                    self._reset_stats()
                    break


def get_twitter_error(e):
    data = json.loads(e.response_data.decode('utf-8'))
    try:
        return (data['errors'][0]['code'], data['errors'][0]['message'])
    except KeyError:
        return None


class AlreadyFavoritedError(Exception):
    pass


class LimitReachedError(Exception):
    pass


class SuccessLimitReachedError(Exception):
    pass
