from django import template

from muffin.controllers import time_to_read

register = template.Library()

register.simple_tag(time_to_read)
