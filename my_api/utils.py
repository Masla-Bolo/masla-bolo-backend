import json
from typing import List, Dict, Optional, Tuple
import firebase_admin
from django.contrib.gis.geos import Polygon, MultiPolygon
import requests
from django.conf import settings

import requests
import re
from firebase_admin import messaging
from firebase_admin import credentials

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {
                "success": "False",
                "message": "Something went wrong!",
                "data": str(exc),
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        if isinstance(exc, ValidationError):
            error_message = ""
            if "email" in response.data or "username" in response.data:
                error_message = "Email or Username already exists or is invalid."
            else:
                error_message = "Bad Request. Check your input data."

            return Response(
                {
                    "success": "False",
                    "message": error_message,
                    "data": response.data,
                    "code": status.HTTP_400_BAD_REQUEST,
                }
            )

        return Response(
            {
                "success": "False",
                "message": "Bad Request",
                "data": response.data,
                "code": status.HTTP_400_BAD_REQUEST,
            }
        )

    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        return Response(
            {
                "success": "False",
                "message": response.data.get("detail", "Unauthorized access"),
                "data": response.data,
                "code": status.HTTP_401_UNAUTHORIZED,
            }
        )

    elif response.status_code == status.HTTP_404_NOT_FOUND:
        return Response(
            {
                "success": "False",
                "message": "Resource not found",
                "data": response.data,
                "code": status.HTTP_404_NOT_FOUND,
            }
        )

    elif response.status_code == status.HTTP_403_FORBIDDEN:
        return Response(
            {
                "success": "False",
                "message": "Permission Denied",
                "data": response.data,
                "code": status.HTTP_403_FORBIDDEN,
            }
        )

    elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        return Response(
            {
                "success": "False",
                "message": "Method Not Allowed",
                "data": response.data.get("detail", "Method not allowed"),
                "code": status.HTTP_405_METHOD_NOT_ALLOWED,
            }
        )

    return response


def send_push_notification(notification):
    if not firebase_admin._apps:
        cred = credentials.Certificate(settings.FIREBASE_SERVICE)
        firebase_admin.initialize_app(cred)

    data_payload = {
        "screen": str(notification.screen),
        "screen_id": str(notification.screen_id),
        "title": str(notification.title),
        "description": str(notification.description),
        "created_at": str(notification.created_at),
    }
    tokens = notification.user.fcm_tokens
    if not isinstance(tokens, list):
        tokens = [tokens]

    tokens = [str(token) for token in tokens]
    message = messaging.MulticastMessage(
        data=data_payload,
        notification=messaging.Notification(title=str(notification.title)),
        tokens=tokens,
    )
    print(f"TITLE IS {notification.title}")
    print(f"Description IS {notification.description}")
    try:
        response = messaging.send_each_for_multicast(message)
        for i, resp in enumerate(response.responses):
            if resp.success:
                print(f"Notification successfully sent to token {tokens[i]}")
            else:
                print(
                    f"Failed to send notification to token {tokens[i]}: {resp.exception}"
                )
        print(f"Notification Sent, Response is: {response}")
        return {
            "status": "success",
            "success_count": response.success_count,
            "failure_count": response.failure_count,
            "responses": response.responses,
        }
    except Exception as e:
        print(f"Notification Not Sent, Exception is: {e}")
        return {"status": "error", "error": str(e)}


def find_official_for_point(point):
    from .models import MyApiOfficial

    try:
        official = MyApiOfficial.objects.filter(area_range__contains=point).first()
        return official if official else None
    except MyApiOfficial.DoesNotExist:
        return None


def get_district_boundary(district_name, city, country):
    """
    Fetch and plot the boundary of a specific district within a city.

    Parameters:
    district_name (str): Name of the district
    city (str): Name of the city
    country (str): Name of the country

    Returns:
    list: List of coordinate pairs forming the boundary
    """
    search_query = f"{district_name}, {city}, {country}"

    # Nominatim API endpoint
    nominatim_url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": search_query,
        "format": "json",
        "polygon_geojson": 1,
        "limit": 10,
        "featuretype": "district",
        "addressdetails": 1,
    }

    headers = {"User-Agent": "district_boundary_fetcher/1.0"}

    try:
        response = requests.get(nominatim_url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()

        if not data:
            raise ValueError(f"No results found for {search_query}")

        # Filter results to find the most relevant district match
        district_result = None
        for result in data:
            address = result.get("address", {})
            # Check if this result is specifically for the district we're looking for
            if (
                address.get("suburb", "").lower() == district_name.lower()
                or address.get("district", "").lower() == district_name.lower()
                or address.get("neighbourhood", "").lower() == district_name.lower()
            ):
                district_result = result
                break

        if not district_result:
            district_result = data[0]

        # Get the geometry
        geojson = district_result.get("geojson")

        if not geojson:
            raise ValueError(f"No boundary data found for {district_name}")

        # Get coordinates based on geometry type (Mainly Polygon is needed)
        if geojson["type"] == "Polygon":
            coordinates = geojson["coordinates"][0]
        elif geojson["type"] == "MultiPolygon":
            coordinates = max(geojson["coordinates"], key=lambda x: len(x[0]))[0]
        else:
            raise ValueError(f"Unsupported geometry type: {geojson['type']}")

        return coordinates

    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

import requests
from django.contrib.gis.geos import GEOSGeometry

def get_polygon_from_area_name(area_name: str):
    """
    Fetches a polygon GEOSGeometry object from an area name using OpenStreetMap Nominatim API.

    Parameters:
        area_name (str): Name of the area to search for.

    Returns:
        tuple: (polygon: GEOSGeometry or None, error_message: str or None)
    """
    try:
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": area_name,
            "format": "json",
            "polygon_geojson": 1
        }
        headers = {"User-Agent": "issue-tracker-app"}

        response = requests.get(nominatim_url, params=params, headers=headers)
        data = response.json()

        if not data or "geojson" not in data[0]:
            return None, "Polygon not found for the given area."

        geojson = data[0]["geojson"]
        polygon = GEOSGeometry(str(geojson))

        return polygon, None

    except Exception as e:
        return None, f"Error fetching polygon: {str(e)}"



def remove_keys_from_dict(d: dict, keys: list):
    temp_dict = d
    for key in keys:
        temp_dict.pop(key)
    return temp_dict

def get_coordinates_from_geojson(geojson: dict) -> Optional[list]:
    """
    Extract coordinates from a GeoJSON object.

    Parameters:
    geojson (dict): GeoJSON object

    Returns:
    list: List of coordinates
    """
    if not geojson or "coordinates" not in geojson:
        return None

    if geojson["type"] == "Polygon":
        return geojson["coordinates"][0]
    elif geojson["type"] == "MultiPolygon":
        return max(geojson["coordinates"], key=lambda x: len(x[0]))[0]
    else:
        return None
    
import requests

CATEGORY_EMERGENCY_TAGS = {
    "electric": [{"key": "power", "value": "substation"}],
    "gas": [{"key": "man_made", "value": "gas_meter"}],
    "water": [{"key": "man_made", "value": "water_works"}],
    "waste": [{"key": "amenity", "value": "waste_disposal"}],
    "sewerage": [{"key": "man_made", "value": "wastewater_plant"}],
    "stormwater": [{"key": "man_made", "value": "storm_drain"}],
    
    "roads_potholes": [{"key": "highway", "value": "service"}],
    "road_safety": [{"key": "highway", "value": "traffic_signals"}],
    "street_lighting": [{"key": "highway", "value": "street_lamp"}],
    "traffic_signals": [{"key": "highway", "value": "traffic_signals"}],
    "parking_violations": [{"key": "amenity", "value": "parking"}],
    "sidewalk_maintenance": [{"key": "footway", "value": "sidewalk"}],
    
    "public_transportation": [{"key": "public_transport", "value": "station"}],
    "public_toilets": [{"key": "amenity", "value": "toilets"}],
    "zoning_planning": [{"key": "office", "value": "government"}],
    
    "parks_recreation": [{"key": "leisure", "value": "park"}],
    "tree_vegetation_issues": [{"key": "natural", "value": "tree"}],
    "illegal_dumping": [{"key": "amenity", "value": "waste_disposal"}],
    "noise_pollution": [{"key": "office", "value": "environment"}],
    "environmental_hazards": [{"key": "man_made", "value": "pollution"}],
    "air_quality": [{"key": "man_made", "value": "monitoring_station"}],
    
    "animal_control": [{"key": "office", "value": "government"}],
    "building_safety": [{"key": "amenity", "value": "police"}],
    "fire_safety": [{"key": "emergency", "value": "fire_station"}],
    "public_health": [{"key": "amenity", "value": "hospital"}],
    "public_safety": [{"key": "amenity", "value": "police"}],
    "vandalism_graffiti": [{"key": "amenity", "value": "police"}],
    
    "other": [{"key": "office", "value": "government"}],
}


def get_emergency_contact(issue):
    if not issue.location or not issue.categories:
        return {"error": "Missing location or categories"}

    lat, lon = issue.location.y, issue.location.x
    category = issue.categories[0].lower()

    tags = CATEGORY_EMERGENCY_TAGS.get(category)
    if not tags:
        return {"error": f"No emergency service mapped for category: {category}"}

    for tag in tags:
        query = f"""
        [out:json];
        node["{tag['key']}"="{tag['value']}"](around:5000,{lat},{lon});
        out body 1;
        """
        response = requests.post("https://overpass-api.de/api/interpreter", data=query)
        if response.status_code == 200:
            data = response.json()
            if data["elements"]:
                el = data["elements"][0]
                return {
                    "name": el.get("tags", {}).get("name", "Unnamed Location"),
                    "type": tag["value"],
                    "address": el.get("tags", {}).get("addr:full", "N/A"),
                    "coordinates": {"lat": el["lat"], "lon": el["lon"]}
                }

    return {"error": "No emergency services found nearby"}

class OSMPolygonExtractor:
    def __init__(self):
        self.overpass_url = "http://overpass-api.de/api/interpreter"
    
    def get_area_polygon(self, area_name: str, area_type: str = "any") -> Optional[Dict]:
        """
        Get polygon coordinates for a named area from OpenStreetMap.
        
        Args:
            area_name (str): Name of the area to search for
            area_type (str): Type of area - 'city', 'country', 'state', 'county', or 'any'
        
        Returns:
            Dict containing polygon data or None if not found
        """
        try:
            # Build the Overpass query
            query = self._build_query(area_name, area_type)
            
            # Make the API request
            response = requests.post(
                self.overpass_url,
                data={'data': query},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get('elements'):
                print(f"No area found for '{area_name}'")
                return None
            
            # Process the response
            return self._process_response(data, area_name)
            
        except requests.RequestException as e:
            print(f"Request error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    def _build_query(self, area_name: str, area_type: str) -> str:
        """Build Overpass QL query for the area."""
        type_filters = {
            'city': '["place"~"^(city|town|village)$"]',
            'country': '["admin_level"="2"]',
            'state': '["admin_level"~"^(3|4)$"]',
            'county': '["admin_level"~"^(5|6)$"]',
            'any': ''
        }
        
        type_filter = type_filters.get(area_type, '')
        
        query = f"""
        [out:json][timeout:25];
        (
          relation["name"="{area_name}"]{type_filter}["type"="boundary"];
          way["name"="{area_name}"]{type_filter};
        );
        out geom;
        """
        
        return query
    
    def _process_response(self, data: Dict, area_name: str) -> Dict:
        """Process the Overpass API response."""
        
        elements = data['elements']
        best_element = None
        for element in elements:
            if element.get('type') == 'relation':
                best_element = element
                break
        
        if not best_element and elements:
            best_element = elements[0]
        
        if not best_element:
            return None
        
        # Extract polygon coordinates
        polygon_coords = self._extract_coordinates(best_element)
        
        result = {
            'name': area_name,
            'osm_id': best_element.get('id'),
            'type': best_element.get('type'),
            'tags': best_element.get('tags', {}),
            'polygon': polygon_coords,
            'bounds': self._calculate_bounds(polygon_coords) if polygon_coords else None
        }
        
        return result
    
    def _extract_coordinates(self, element: Dict) -> List[List[Tuple[float, float]]]:
        """Extract coordinates from OSM element."""
        
        if element.get('type') == 'way':
            # Simple way - return single polygon
            if 'geometry' in element:
                coords = [(node['lon'], node['lat']) for node in element['geometry']]
                return [coords] if coords else []
        
        elif element.get('type') == 'relation':
            # Relation - can have multiple polygons (multipolygon)
            polygons = []
            
            for member in element.get('members', []):
                if member.get('type') == 'way' and 'geometry' in member:
                    coords = [(node['lon'], node['lat']) for node in member['geometry']]
                    if coords:
                        polygons.append(coords)
            
            return polygons
        
        return []
    
    def _calculate_bounds(self, polygon_coords: List[List[Tuple[float, float]]]) -> Dict[str, float]:
        """Calculate bounding box for the polygon."""
        
        if not polygon_coords:
            return None
        
        all_coords = []
        for polygon in polygon_coords:
            all_coords.extend(polygon)
        
        if not all_coords:
            return None
        
        lons = [coord[0] for coord in all_coords]
        lats = [coord[1] for coord in all_coords]
        
        return {
            'min_lon': min(lons),
            'max_lon': max(lons),
            'min_lat': min(lats),
            'max_lat': max(lats)
        }


HEADERS = {
    "User-Agent": "MyIssueApp (contact@yourdomain.com)",
    "Accept-Language": "en"
}


def reverse_geocode(lat, lon):
    """Reverse geocode to get area, city, and country from coordinates."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",
        "lat": lat,
        "lon": lon,
        "zoom": 18,
        "addressdetails": 1
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        address = resp.json().get("address", {})
        # Optional: log full address for debugging
        return {
            "neighbourhood": address.get("neighbourhood"),
            "suburb": address.get("suburb"),
            "village": address.get("village"),
            "town": address.get("town"),
            "city": address.get("city"),
            "municipality": address.get("municipality"),
            "state_district": address.get("state_district"),
            "county": address.get("county"),
            "country": address.get("country") or "Unknown"
        }
    except Exception as e:
        print(f"❌ Reverse geocode error at ({lat}, {lon}): {e}")
        return {}



def fetch_boundary_from_overpass(area_name):
    """
    Query Overpass API to fetch boundary (geometry) for a named area.
    Supports: administrative boundaries, place-based polygons.
    """
    query = f"""
    [out:json][timeout:30];
    (
      relation["name"="{area_name}"]["boundary"];
      relation["name"="{area_name}"]["place"~"neighbourhood|suburb|quarter|locality|block"];
      way["name"="{area_name}"]["boundary"];
      way["name"="{area_name}"]["place"~"neighbourhood|suburb|quarter|locality|block"];
    );
    out geom;
    """

    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={
                "User-Agent": "MyIssueApp (contact@yourdomain.com)",
                "Accept-Language": "en"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Overpass error for {area_name}: {e}")
        return None

    polygons = []

    for element in data.get("elements", []):
        if "geometry" not in element:
            continue

        coords = [(pt["lon"], pt["lat"]) for pt in element["geometry"]]
        if len(coords) >= 4 and coords[0] == coords[-1]:  # closed loop
            try:
                poly = Polygon(coords)
                polygons.append(poly)
            except Exception:
                continue

    if polygons:
        return MultiPolygon(polygons)
    return None


def assign_area_names_to_issues():
    import time
    from my_api.models import Issue, AreaLocation
    issues = Issue.objects.filter(location__isnull=False, area__isnull=True)

    for issue in issues:
        lat, lon = issue.location.y, issue.location.x
        address = reverse_geocode(lat, lon)

        town = (
            address.get("suburb")
            or address.get("neighbourhood")
            or address.get("village")
            or address.get("town")
        )
        city = (
            address.get("city")
            or address.get("municipality")
            or address.get("state_district")
            or address.get("county")
        )
        country = address.get("country") or "Unknown"

        if not town:
            print(f"⚠️ No town found for issue '{issue.title}' at ({lat}, {lon})")
            continue

        city = city or "Unknown"

        area = AreaLocation.objects.filter(name=town, city_name=city, country=country).first()

        if not area:
            print(f"🌐 Fetching boundary for: {town}, {city}, {country}")
            boundary = fetch_boundary_from_overpass(town)

            if boundary:
                area = AreaLocation.objects.create(
                    name=town,
                    city_name=city,
                    country=country,
                    boundary=boundary
                )
                print(f"✅ Created with boundary: {town}, {city}, {country}")
            else:
                area = AreaLocation.objects.create(
                    name=town,
                    city_name=city,
                    country=country,
                    boundary=None
                )
                print(f"⚠️ Created without boundary: {town}, {city}, {country}")

        issue.area = area
        issue.save(update_fields=["area"])
        print(f"✔️ Assigned: Issue '{issue.title}' → {town}, {city}, {country}")

        time.sleep(1)  # Respect rate limits


def get_issue_counts_by_area():
    from my_api.models import Issue
    from django.db.models import Count
    results = (
        Issue.objects
        .filter(area__isnull=False)
        .values("area__name", "area__city_name")
        .annotate(issue_count=Count("id"))
        .order_by("-issue_count")
    )

    for row in results:
        print(f"📍 {row['area__name']}, {row['area__city_name']} → 🧾 {row['issue_count']} issues")
    
    return results

# import os
# import google.generativeai as genai
# from django.conf import settings

# genai.configure(api_key=settings.GEMINI_API_KEY)

# def generate_emergency_contact_prompt(issue_type: str, city: str) -> str:
#     return (
#         f"You are helping to retrieve emergency contact info in Pakistan.\n"
#         f"Provide the following:\n"
#         f"1. Primary contact: official emergency service (email and phone) related to {issue_type} issues in {city}.\n"
#         f"2. Secondary contact: contact number and email of the District Commissioner of {city}.\n"
#         f"Return in a parsable JSON format like:\n"
#         f"{{\n"
#         f'  "primary_contact": {{"type": "...", "phone": "...", "email": "..." }},\n'
#         f'  "secondary_contact": {{"type": "District Commissioner", "phone": "...", "email": "..." }}\n'
#         f"}}"
#     )


def get_emergency_contact_info(issue_type, city, area):
    if not all([issue_type, city, area]):
        return {"error": "Missing required parameters: issue_type, city, or area"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        f"You are an emergency information assistant for {city}. "
        f"Provide ONLY valid JSON with emergency contacts for {issue_type} issues in {area}, {city}.\n\n"
        "Structure:\n"
        "{\n"
        '  "primary_contact": {"type": "Service Name", "phone": "number", "email": "address"},\n'
        '  "secondary_contact": {"type": "District Commissioner", "phone": "number", "email": "address"}\n'
        "}\n\n"
        "Rules:\n"
        "- Phone numbers best be in +9XXXXXXXXXXX format or 021XXXXXXXX\n"
        "- Respond ONLY with valid JSON, no additional text\n"
        "- If information is unavailable, give the general emergency info for the city"
    )

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.3
        }
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        
        content = response.json()
        if "candidates" not in content or not content["candidates"]:
            return {"error": "No response from Gemini API"}
        
        raw_text = content["candidates"][0]["content"]["parts"][0]["text"]
        
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not json_match:
            return {"error": "No JSON found in response", "response": raw_text}
        
        json_text = json_match.group(0)
        result = json.loads(json_text)
        
        required_keys = {"primary_contact", "secondary_contact"}
        if not all(key in result for key in required_keys):
            return {"error": "Invalid response structure", "response": result}
        
        return result

    except requests.exceptions.RequestException as e:
        return {"error": "API request failed", "details": str(e)}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response", "response": raw_text}
    except KeyError as e:
        return {"error": f"Missing key in response: {str(e)}", "response": content}
    except Exception as e:
        return {"error": "Unexpected error", "details": str(e)}



# if __name__ == "__main__":
    # populator = AreaLocationPopulator()
    # populator.populate_city_areas("Karachi")
    # assign_areas_to_issues()

# if __name__ == "__main__":
    # Example usage
    # district_name = "Nazimabad"
    # city = "Karachi"
    # country = "Pakistan"
    
    # coordinates = get_district_boundary(district_name, city, country)
    # if coordinates:
    #     print(f"Coordinates for {district_name}: {coordinates}")
    # else:
    #     print("Failed to fetch coordinates.")