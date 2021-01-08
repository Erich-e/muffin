from functools import partial, wraps
from typing import Callable

from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, UsernameField
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .constants import PAGE_SIZE
from .controllers import (
    UserdataFormatter,
    construct_feeds_for_website,
    construct_new_articles,
    get_quote,
)
from .models import Article, Feed, ReadEvent


@require_GET
def index(request) -> HttpResponse:
    query = Article.objects.select_related("feed").order_by("-published_date")
    if request.user.is_authenticated:
        query = query.filter(feed__followers=request.user)
    paginator = Paginator(query, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "muffin/index.html",
        {"page_obj": page_obj},
    )


@require_GET
def poll_rss(request) -> HttpResponse:
    feeds = Feed.objects.all()

    for feed in feeds:
        new_articles = construct_new_articles(feed)
        for new_article in new_articles:
            new_article.save()

        if feed.rss_data["bozo"]:
            feed.is_bozo = True
            feed.save()

    return HttpResponse()


@require_POST
@login_required
def mark_read(request) -> HttpResponse:
    try:
        article = Article.objects.get(pk=request.POST["article"])
    except (KeyError, Article.DoesNotExist):
        raise Http404
    read_event = ReadEvent(user=request.user, article=article, read_at=timezone.now())
    read_event.save()
    return HttpResponse()


@require_GET
def article_content(request, article_id) -> HttpResponse:
    article = get_object_or_404(Article, pk=article_id)
    return HttpResponse(article.text)


class LoginForm(forms.ModelForm):
    title = "Login"

    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = get_user_model()
        fields = ("email", "password")


@require_http_methods(["GET", "POST"])
def login_view(request) -> HttpResponse:
    if request.method == "GET":
        form = LoginForm()
    else:
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                login(request, user)
                return redirect("muffin:index")
            else:
                form.add_error(None, ValidationError("Failed to Authenticate"))
    return render(request, "muffin/simple_form.html", {"form": form})


def logout_view(request) -> HttpResponse:
    logout(request)
    return redirect("muffin:index")


@login_required
@require_http_methods(["GET", "POST"])
def download_data(request) -> HttpResponse:
    formatter = UserdataFormatter(request.user)
    return JsonResponse(formatter.as_dict())


class ConfirmationForm(forms.Form):
    title = "Are you sure?"


@login_required
@require_http_methods(["GET", "POST"])
def delete_account(request) -> HttpResponse:
    if request.method == "GET":
        form = ConfirmationForm()
        return render(request, "muffin/simple_form.html", {"form": form})
    else:
        request.user.delete()
        logout(request)
        return redirect("muffin:index")


@login_required
@require_GET
def reading_speed(request) -> HttpResponse:
    return render(request, "muffin/reading_speed.html")


@login_required
@require_http_methods(["GET", "POST"])
def time_wpm(request) -> HttpResponse:
    if request.method == "GET":
        quote = get_quote()
        return render(request, "muffin/quote.html", {"quote": quote})
    else:
        request.user.wpm = int(request.POST["wpm"])
        request.user.save()
        return HttpResponse()


class SignupForm(forms.ModelForm):
    title = "Sign Up"

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Password confirmation",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        strip=False,
    )

    class Meta:
        model = get_user_model()
        fields = ["email"]

    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match", code="password_mismatch")
        return p2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


@require_http_methods(["GET", "POST"])
def sign_up_view(request) -> HttpResponse:
    if request.method == "GET":
        form = SignupForm()
    else:
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save(commit=True)
            login(request, user)
            return redirect("muffin:manage_feeds")

    return render(request, "muffin/simple_form.html", {"form": form})


@login_required
@require_GET
def manage_feeds(request) -> HttpResponse:
    feed_query = Feed.objects.prefetch_related("followers").order_by("title")
    search_string = request.GET.get("search")
    if search_string:
        terms = search_string.split()
        for term in terms:
            feed_query = feed_query.filter(title__icontains=term)
    feeds = feed_query.all()
    return render(
        request,
        "muffin/manage_feeds.html",
        {
            "feeds": feeds,
            "search_string": search_string,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def add_feed(request) -> HttpResponse:
    if request.method == "GET":
        feed = Feed.from_url(request.GET["url"])
    else:
        feed = Feed.from_url(request.POST["url"])
        if feed is not None:
            feed.save()
            request.user.followed_feeds.add(feed)
            request.user.save()
            new_articles = construct_new_articles(feed)
            for new_article in new_articles:
                new_article.save()
            return redirect("muffin:manage_feeds")
    return render(request, "muffin/add_feed_confirmation.html", {"feed": feed})


@login_required
@require_http_methods(["GET", "POST"])
def find_feeds(request) -> HttpResponse:
    if request.method == "GET":
        feeds = construct_feeds_for_website(request.GET["url"])
        existing_feeds = Feed.objects.filter(url__in=[f.url for f in feeds]).all()
        existing_urls = [ef.url for ef in existing_feeds]
    if request.method == "POST":
        for name, value in request.POST.items():
            if name.startswith("url-") and value == "on":
                url = name.removeprefix("url-")
                feed = Feed.from_url(url)
                feed.save()
                request.user.followed_feeds.add(feed)
                new_articles = construct_new_articles(feed)
                for new_article in new_articles:
                    new_article.save()
        return redirect("muffin:manage_feeds")

    return render(
        request,
        "muffin/find_feeds_confirmation.html",
        {"feeds": feeds, "existing_urls": existing_urls},
    )


@login_required
@require_POST
def follow(request) -> HttpResponse:
    feed = get_object_or_404(Feed, pk=request.POST.get("feed"))
    if feed not in request.user.followed_feeds.all():
        request.user.followed_feeds.add(feed)
        request.user.save()
    return HttpResponse()


@login_required
@require_POST
def unfollow(request) -> HttpResponse:
    feed = get_object_or_404(Feed, pk=request.POST.get("feed"))
    if feed in request.user.followed_feeds.all():
        request.user.followed_feeds.remove(feed)
        request.user.save()
    return HttpResponse()
