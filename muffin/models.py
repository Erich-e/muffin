from typing import Optional

import feedparser
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import AVERAGE_WPM


class Feed(models.Model):
    title = models.CharField(max_length=64, db_index=True)
    description = models.CharField(max_length=200)
    url = models.URLField(max_length=256, unique=True)
    favicon_url = models.URLField(max_length=256)
    is_bozo = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rss_data = None

    @classmethod
    def from_url(cls, url: str) -> Optional["Feed"]:
        from .controllers import set_url_scheme, get_favicon_url

        url = set_url_scheme(url, "http")
        feed = cls(url=url)
        if feed.rss_data["bozo"]:
            return None
        feed.title = feed.rss_data["channel"]["title"]
        feed.description = feed.rss_data["channel"].get("description", "")
        feed.favicon_url = get_favicon_url(feed.rss_data["channel"]["link"])
        return feed

    @property
    def most_recent(self) -> Optional["Article"]:
        return self.article_set.order_by("-published_date").first()

    @property
    def rss_data(self) -> dict:
        if self._rss_data is None:
            self._rss_data = feedparser.parse(self.url)
        return self._rss_data


class Article(models.Model):
    feed = models.ForeignKey(Feed, on_delete=models.CASCADE)
    source_id = models.CharField(max_length=64, null=True)
    published_date = models.DateTimeField(db_index=True)
    url = models.URLField(max_length=200, db_index=True)
    image_url = models.URLField(max_length=200)
    title = models.CharField(max_length=64)
    num_words = models.IntegerField(null=True)


class User(AbstractUser):
    wpm = models.IntegerField(default=AVERAGE_WPM)
    followed_feeds = models.ManyToManyField(Feed, related_name="followers")


class ReadEvent(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_index=True
    )
    article = models.ForeignKey(Article, on_delete=models.CASCADE, db_index=True)
    read_at = models.DateTimeField(db_index=True)
