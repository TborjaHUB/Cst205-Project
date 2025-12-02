import requests
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class UnsplashAPI:
    """
    A simple wrapper for the Unsplash API to fetch random images by keyword.
    """

    BASE_URL = "https://api.unsplash.com"

    def __init__(self):
        self.access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        if not self.access_key:
            raise ValueError("UNSPLASH_ACCESS_KEY not found in environment variables")

        self.headers = {
            "Authorization": f"Client-ID {self.access_key}"
        }

    def get_random_image(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a random image from Unsplash based on a keyword query.

        Args:
            query: Search keyword(s) for the image

        Returns:
            Dictionary containing image data including URL, author, and metadata
            Returns None if the request fails
        """
        endpoint = f"{self.BASE_URL}/photos/random"

        params = {
            "query": query,
            "orientation": "landscape",
            "content_filter": "high" 
        }

        try:
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching image from Unsplash: {e}")
            return None

    def get_image_url(self, query: str) -> Optional[str]:
        """
        Convenience method to get just the image URL for a given query.

        Args:
            query: Search keyword(s) for the image

        Returns:
            Direct URL to the image, or None if request fails
        """
        data = self.get_random_image(query)
        if data and "urls" in data:
            return data["urls"]["regular"]
        return None

    def get_image_with_metadata(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Get a random image along with useful metadata.

        Args:
            query: Search keyword(s) for the image

        Returns:
            Dictionary with 'url', 'author', 'description', and 'link' keys
            Returns None if request fails
        """
        data = self.get_random_image(query)
        if data:
            return {
                "url": data["urls"]["regular"],
                "author": data.get("user", {}).get("name", "Unknown"),
                "description": data.get("description") or data.get("alt_description", "No description"),
                "link": data.get("links", {}).get("html", ""),
                "raw_data": data
            }
        return None
