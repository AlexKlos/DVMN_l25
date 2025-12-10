import math
import requests
from django.conf import settings


def fetch_coordinates(address: str):
    base_url = 'https://geocode-maps.yandex.ru/1.x'

    try:
        response = requests.get(
            base_url,
            params={
                'geocode': address,
                'apikey': settings.GEOCODE_APIKEY,
                'format': 'json',
            },
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        members = data['response']['GeoObjectCollection']['featureMember']

        if not members:
            return None
        
        point = members[0]['GeoObject']['Point']['pos']
        lon_str, lat_str = point.split()

        return float(lon_str), float(lat_str)
    
    except (requests.RequestException, KeyError, ValueError):
        return None


def distance_km(a, b) -> float:
    lon1, lat1 = a
    lon2, lat2 = b

    lon1 = math.radians(lon1)
    lat1 = math.radians(lat1)
    lon2 = math.radians(lon2)
    lat2 = math.radians(lat2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2

    return 2 * 6373 * math.atan2(math.sqrt(h), math.sqrt(1 - h))
