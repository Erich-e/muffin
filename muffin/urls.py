from functools import partial

from django.urls import path

from . import views

app_name = "muffin"
urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("sign_up/", views.sign_up_view, name="signup"),
    path("download_data/", views.download_data, name="download_data"),
    path("delete_account/", views.delete_account, name="delete_account"),
    path("manage_feeds/", views.manage_feeds, name="manage_feeds"),
    path("add_feed/", views.add_feed, name="add_feed"),
    path("find_feeds/", views.find_feeds, name="find_feeds"),
    path("stats/", views.stats, name="stats"),
    path("reading_speed/", views.reading_speed, name="reading_speed"),
    path("api/poll_rss/", views.poll_rss, name="poll_rss"),
    path("api/mark_read/", views.mark_read, name="mark_read"),
    path(
        "api/articles/<int:article_id>/content",
        views.article_content,
        name="article_content",
    ),
    path("api/follow", views.follow, name="follow"),
    path("api/unfollow", views.unfollow, name="unfollow"),
    path("api/time_wpm", views.time_wpm, name="time_wpm"),
]
