import html
import math
import time
import urllib
from datetime import datetime
from typing import Optional

import feedfinder2
import feedparser
from django.forms.models import model_to_dict
from django.utils import timezone
from newspaper import Article as ScrapedArticle
from newspaper.configuration import Configuration as ScraperConfigBase

from .constants import AVERAGE_WPM
from .models import Article, Feed, ReadEvent, User


def struct_time_to_datetime(struct_time: time.struct_time):
    ts = time.mktime(struct_time)
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def construct_new_articles(feed: Feed) -> list[Article]:
    new_rss_entries = ArticlePuller(feed).pull_new()
    builder = ArticleBuilder(feed)
    return [builder.from_rss(new_rss_entry) for new_rss_entry in new_rss_entries]


def construct_feeds_for_website(website_url: str) -> list[Feed]:
    feed_urls = feedfinder2.find_feeds(website_url)
    if not feed_urls:
        if website_url.endswith("/"):
            subdir = "rss"
        else:
            subdir = "/rss"
        feed_urls = feedfinder2.find_feeds(website_url + subdir)
    return [Feed.from_url(feed_url) for feed_url in feed_urls]


def time_to_read(article: Article, user: User) -> int:
    if user.is_authenticated:
        wpm = user.wpm
    else:
        wpm = AVERAGE_WPM
    return math.ceil(article.num_words / wpm)


def set_url_scheme(url: str, scheme: str) -> str:
    """
    Converts urls without a scheme to new scheme.
    Updates urls with a scheme to use the new scheme
    """
    coerced_url = feedfinder2.coerce_url(url)
    parsed_url = urllib.parse.urlparse(coerced_url)
    http_url = parsed_url._replace(scheme=scheme)
    return urllib.parse.urlunparse(http_url)


class TimerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        print("Time taken:", time.time() - start)
        return response


class ArticlePuller:
    def __init__(self, feed: Feed):
        self.feed = feed
        # no optional chaining :(
        self.cutoff_date = getattr(feed.most_recent, "published_date", None)

    def pull_new(self) -> list[dict]:
        return [
            rss_entry
            for rss_entry in self.feed.rss_data["entries"]
            if self.is_new_entry(rss_entry)
        ]

    def is_new_entry(self, rss_entry: dict) -> bool:
        return "published_parsed" in rss_entry and (
            self.cutoff_date is None
            or struct_time_to_datetime(rss_entry["published_parsed"]) > self.cutoff_date
        )


class ScraperConfig(ScraperConfigBase):
    def __init__(self):
        super().__init__()
        self.keep_article_html = True


class ArticleBuilder:
    scraper_config = ScraperConfig()

    def __init__(self, feed: Feed):
        self.feed = feed

    def from_rss(self, rss_entry: dict) -> Article:
        scraped_article = ScrapedArticle(rss_entry["link"], config=self.scraper_config)
        scraped_article.download()
        scraped_article.parse()
        published_date = struct_time_to_datetime(rss_entry["published_parsed"])

        return Article(
            feed=self.feed,
            source_id=rss_entry["id"],
            published_date=published_date,
            url=rss_entry["link"],
            image_url=scraped_article.top_image,
            title=scraped_article.title,
            num_words=len(scraped_article.text.split()),
        )


class UserdataFormatter:
    def __init__(self, user: User):
        self.user = user

    def as_dict(self) -> dict:
        return {
            "user": model_to_dict(
                self.user,
                fields=[
                    "last_login",
                    "is_superuser",
                    "username",
                    "email",
                    "is_active",
                    "date_joined",
                    "wpm",
                ],
            ),
            "followed_feeds": [
                model_to_dict(feed) for feed in self.user.followed_feeds.all()
            ],
            "read_events": [
                {
                    "read_at": read_event.read_at.isoformat(),
                    "article": model_to_dict(read_event.article),
                }
                for read_event in self.user.readevent_set.select_related(
                    "article"
                ).all()
            ],
        }
