import json
from typing import List, Dict, Optional, Tuple
import folium

import requests
from firebase_admin import messaging

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