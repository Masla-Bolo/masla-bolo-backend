import json
from typing import Optional

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

    # Parameters for the API request
    # Adding specific parameters to target district-level boundaries
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