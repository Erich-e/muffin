from django import template

from muffin.controllers import format_time_to_read, format_article_date

register = template.Library()

register.simple_tag(format_time_to_read)
register.simple_tag(format_article_date)
