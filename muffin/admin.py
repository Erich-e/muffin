from django.contrib import admin

from .models import Article, Feed, User

admin.site.register(Article)
admin.site.register(Feed)
admin.site.register(User)
