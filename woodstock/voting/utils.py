import logging
import requests
import urllib

from django.conf import settings

from django_countries.data import COUNTRIES

from models import MozillianGroup, MozillianProfile


logger = logging.getLogger(__name__)


API_RESULTS_LIMIT = 200
REPS_PROFILE_URL = 'https://reps.mozilla.org/u/'


def query_api(url):
    """Helper method to query mozillians.org/Reps API"""
    resp = requests.get(url)

    if not resp.status_code == 200:
        logger.error('Reponse status: {}'.format(resp.status_code))
        return None

    content = resp.json()
    if content['objects']:
        return content['objects'][0]
    return content['objects']


def get_mozillian_by_email(email):
    """Helper method to query Mozillians API v1.."""
    data = {
        'app_name': settings.MOZILLIANS_APP_NAME,
        'app_key': settings.MOZILLIANS_APP_KEY,
        'limit': API_RESULTS_LIMIT,
        'email': email
    }

    url = settings.MOZILLIANS_API_URL + '?' + urllib.urlencode(data)
    return query_api(url)


def get_rep_by_mozillian_profile(username):
    """Helper method to query Reps API v1."""
    data = {
        'limit': API_RESULTS_LIMIT,
        'query': username
    }

    url = settings.REPS_API_URL + '?format=json&' + urllib.urlencode(data)
    return query_api(url)


def get_mozillian_by_username(username):
    """Helper method to query Reps API v1 by username."""
    data = {
        'app_name': settings.MOZILLIANS_APP_NAME,
        'app_key': settings.MOZILLIANS_APP_KEY,
        'limit': API_RESULTS_LIMIT,
        'username': username
    }

    url = settings.MOZILLIANS_API_URL + '?' + urllib.urlencode(data)
    return query_api(url)


def update_mozillian_profiles(queryset=None):
    """Sync MozillianProfile objects with mozillians.org"""

    if not queryset:
        queryset = MozillianProfile.objects.all()

    for mozillian in queryset:
        data = get_mozillian_by_email(mozillian.email)

        if not data:
            # Try to fetch by username
            data = get_mozillian_by_username(mozillian.mozillian_username)

            if not data:
                continue

        if 'country' in data:
            mozillian.country = COUNTRIES.get(data['country'].upper(), '').capitalize()
        if 'full_name' in data:
            mozillian.full_name = data['full_name']
        else:
            mozillian.full_name = 'Private Mozillian'
        mozillian.email = data['email']
        if 'city' in data:
            mozillian.city = data['city']
        if 'ircname' in data:
            mozillian.ircname = data['ircname']
        if 'photo' in data:
            mozillian.avatar_url = data['photo']
        if 'bio' in data:
            mozillian.bio = data['bio']
        mozillian.save()

        mozillian.tracking_groups.clear()
        groups = []
        if 'groups' in data:
            for group in data['groups']:
                obj, created = MozillianGroup.objects.get_or_create(name=group)
                groups.append(obj)

        mozillian.tracking_groups = groups
        logger.debug('Mozillian succesfully updated.')


def get_object_or_none(model_class, **kwargs):
    """Identical to get_object_or_404, except instead of returning Http404,
    this returns None.

    """
    try:
        return model_class.objects.get(**kwargs)
    except (model_class.DoesNotExist, model_class.MultipleObjectsReturned):
        return None


def fetch_rep_profiles(queryset=None):
    """Sync MozillianProfile objects with reps.mozilla.org"""

    if not queryset:
        queryset = MozillianProfile.objects.all()

    for mozillian in queryset:
        data = get_rep_by_mozillian_profile(mozillian.email)

        if not data:
            continue

        if 'profile' in data and 'display_name' in data['profile']:
            mozillian.reps_display_name = data['profile']['display_name']
        mozillian.save()
        logger.debug('Mozillian succesfully updated.')
