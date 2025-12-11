import math
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone
from geopy.distance import distance

from .models import Location


def _fetch_coordinates_from_api(address: str):
    base_url = 'https://geocode-maps.yandex.ru/1.x'
    try:
        raw_response = requests.get(
            base_url,
            params={
                'geocode': address,
                'apikey': settings.GEOCODE_APIKEY,
                'format': 'json',
            },
            timeout=5,
        )
        raw_response.raise_for_status()
        response = raw_response.json()
        members = response['response']['GeoObjectCollection']['featureMember']
        if not members:
            return None
        point = members[0]['GeoObject']['Point']['pos']
        lon_str, lat_str = point.split()
        return float(lon_str), float(lat_str)
    except (requests.RequestException, KeyError, ValueError):
        return None


def fetch_coordinates(address: str):
    if not address:
        return None

    address_text = address.strip()
    if not address_text:
        return None

    obj, created = Location.objects.get_or_create(address=address_text)
    now = timezone.now()
    month_ago = now - timedelta(days=30)

    if obj.lon is not None and obj.lat is not None and obj.updated_at >= month_ago:
        return obj.lon, obj.lat

    coords = _fetch_coordinates_from_api(address_text)

    if coords is None:
        obj.lon = None
        obj.lat = None
    else:
        obj.lon, obj.lat = coords

    obj.updated_at = now
    obj.save()

    return coords


def distance_km(coords1, coords2) -> float:
    if coords1 is None or coords2 is None:
        return None
    
    lon1, lat1 = coords1
    lon2, lat2 = coords2

    return distance((lat1, lon1), (lat2, lon2)).km
