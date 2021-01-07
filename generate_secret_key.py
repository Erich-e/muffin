#!/usr/bin/env python
from django.core.management.utils import get_random_secret_key

with open(".env", "a+") as f:
    print(f"DJANGO_SECRET={get_random_secret_key()}", file=f)
