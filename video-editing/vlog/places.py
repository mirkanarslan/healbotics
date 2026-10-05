"""GPS -> city name. Online via OpenStreetMap Nominatim (cached per project),
offline fallback via a built-in list of larger cities."""
import json
import math
import re
import urllib.parse
import urllib.request

from .common import load_json, save_json

# (city, country label, lat, lon). Extend freely; nearest city within MAX_KM wins.
CITIES = [
    ("Berlin", "Deutschland", 52.520, 13.405), ("Hamburg", "Deutschland", 53.551, 9.994),
    ("München", "Deutschland", 48.137, 11.575), ("Köln", "Deutschland", 50.938, 6.960),
    ("Frankfurt am Main", "Deutschland", 50.110, 8.682), ("Stuttgart", "Deutschland", 48.776, 9.183),
    ("Düsseldorf", "Deutschland", 51.227, 6.774), ("Dortmund", "Deutschland", 51.514, 7.468),
    ("Essen", "Deutschland", 51.456, 7.012), ("Leipzig", "Deutschland", 51.340, 12.375),
    ("Bremen", "Deutschland", 53.079, 8.802), ("Dresden", "Deutschland", 51.050, 13.738),
    ("Hannover", "Deutschland", 52.376, 9.732), ("Nürnberg", "Deutschland", 49.452, 11.077),
    ("Duisburg", "Deutschland", 51.434, 6.762), ("Bochum", "Deutschland", 51.482, 7.216),
    ("Wuppertal", "Deutschland", 51.256, 7.150), ("Bielefeld", "Deutschland", 52.030, 8.532),
    ("Bonn", "Deutschland", 50.737, 7.098), ("Münster", "Deutschland", 51.961, 7.626),
    ("Mannheim", "Deutschland", 49.487, 8.466), ("Karlsruhe", "Deutschland", 49.007, 8.404),
    ("Augsburg", "Deutschland", 48.371, 10.898), ("Wiesbaden", "Deutschland", 50.078, 8.240),
    ("Mainz", "Deutschland", 49.993, 8.247), ("Aachen", "Deutschland", 50.776, 6.084),
    ("Kiel", "Deutschland", 54.323, 10.123), ("Freiburg", "Deutschland", 47.999, 7.842),
    ("Heidelberg", "Deutschland", 49.399, 8.672), ("Potsdam", "Deutschland", 52.391, 13.064),
    ("Wien", "Österreich", 48.208, 16.373), ("Salzburg", "Österreich", 47.810, 13.055),
    ("Zürich", "Schweiz", 47.377, 8.541), ("Basel", "Schweiz", 47.560, 7.589),
    ("Genf", "Schweiz", 46.204, 6.143), ("Amsterdam", "Niederlande", 52.368, 4.904),
    ("Rotterdam", "Niederlande", 51.924, 4.478), ("Brüssel", "Belgien", 50.850, 4.352),
    ("Paris", "Frankreich", 48.857, 2.352), ("London", "Vereinigtes Königreich", 51.507, -0.128),
    ("Madrid", "Spanien", 40.417, -3.704), ("Barcelona", "Spanien", 41.385, 2.173),
    ("Lissabon", "Portugal", 38.722, -9.139), ("Rom", "Italien", 41.903, 12.496),
    ("Mailand", "Italien", 45.464, 9.190), ("Kopenhagen", "Dänemark", 55.676, 12.568),
    ("Stockholm", "Schweden", 59.329, 18.069), ("Oslo", "Norwegen", 59.913, 10.752),
    ("Prag", "Tschechien", 50.076, 14.438), ("Warschau", "Polen", 52.230, 21.012),
    ("Istanbul", "Türkei", 41.008, 28.978), ("Ankara", "Türkei", 39.933, 32.860),
    ("Antalya", "Türkei", 36.897, 30.713), ("Izmir", "Türkei", 38.424, 27.143),
    ("Dubai", "VAE", 25.205, 55.271), ("Abu Dhabi", "VAE", 24.454, 54.377),
    ("Doha", "Katar", 25.285, 51.531), ("Riad", "Saudi-Arabien", 24.713, 46.675),
    ("Tel Aviv", "Israel", 32.085, 34.782), ("Kairo", "Ägypten", 30.044, 31.236),
    ("New York", "USA", 40.713, -74.006), ("San Francisco", "USA", 37.775, -122.419),
    ("Los Angeles", "USA", 34.052, -118.244), ("Miami", "USA", 25.762, -80.192),
    ("Austin", "USA", 30.267, -97.743), ("Boston", "USA", 42.360, -71.059),
    ("Toronto", "Kanada", 43.653, -79.383), ("Hongkong", "China", 22.319, 114.169),
    ("Shenzhen", "China", 22.543, 114.058), ("Guangzhou", "China", 23.129, 113.264),
    ("Foshan", "China", 23.022, 113.122), ("Shanghai", "China", 31.230, 121.474),
    ("Peking", "China", 39.904, 116.407), ("Singapur", "Singapur", 1.352, 103.820),
    ("Tokio", "Japan", 35.676, 139.650), ("Seoul", "Südkorea", 37.567, 126.978),
    ("Bangkok", "Thailand", 13.756, 100.502), ("Bali", "Indonesien", -8.409, 115.189),
    ("Sydney", "Australien", -33.869, 151.209), ("Melbourne", "Australien", -37.814, 144.963),
    ("Brisbane", "Australien", -27.470, 153.026),
]
MAX_KM = 40


def parse_iso6709(value):
    """'+52.5200+013.4050+034.000/' -> (52.52, 13.405)."""
    m = re.match(r"([+-]\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)", value or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


def gps_from_tags(tags):
    for key in ("com.apple.quicktime.location.iso6709", "location", "location-eng"):
        if tags.get(key):
            return parse_iso6709(tags[key])
    return None


def _km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def offline_city(latlon):
    best = min(CITIES, key=lambda c: _km(latlon, (c[2], c[3])))
    if _km(latlon, (best[2], best[3])) <= MAX_KM:
        return {"city": best[0], "sub": best[1], "source": "offline"}
    return None


def online_city(latlon, lang="de"):
    q = urllib.parse.urlencode({"lat": latlon[0], "lon": latlon[1], "format": "jsonv2",
                                "zoom": 10, "accept-language": lang})
    req = urllib.request.Request(f"https://nominatim.openstreetmap.org/reverse?{q}",
                                 headers={"User-Agent": "healbotics-vlog-cutter/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        addr = json.load(r).get("address", {})
    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
    if not city:
        return None
    sub = addr.get("suburb") or addr.get("city_district") or addr.get("country")
    return {"city": city, "sub": sub, "country": addr.get("country"), "source": "osm"}


def lookup(latlon, cache_path, lang="de", online=True):
    """City for a GPS point. Rounds to ~1 km for the cache key."""
    key = f"{latlon[0]:.2f},{latlon[1]:.2f}"
    cache = load_json(cache_path, {})
    if key in cache:
        return cache[key]
    result = None
    if online:
        try:
            result = online_city(latlon, lang)
        except Exception:
            result = None  # offline or blocked: fall back silently
    result = result or offline_city(latlon)
    cache[key] = result
    save_json(cache_path, cache)
    return result
