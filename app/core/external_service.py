import requests
import logging
from requests.exceptions import RequestException, HTTPError, Timeout


class ExternalService:
    """
    Base class for interacting with external services.
    Handles HTTP requests, authentication, error handling, and retries.
    """

    def __init__(self, base_url: str, api_key: str = None, timeout: int = 10):
        """
        Initialize the service with the base URL, optional API key, and timeout.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def _handle_response(self, response):
        """
        Process HTTP responses and handle errors.
        """
        try:
            response.raise_for_status()
            return response.json()
        except HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} - Response: {response.text}")
        except RequestException as req_err:
            logging.error(f"Request error: {req_err}")
        return None

    def request(self, method: str, endpoint: str, params=None, data=None, headers=None, retries: int = 3):
        """
        Generalized request method with retry logic.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        attempt = 0
        headers = headers or {}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        while attempt < retries:
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=headers,
                    timeout=60
                )
                return self._handle_response(response)

            except Timeout:
                logging.warning(f"Request timeout for {url}. Retrying {attempt + 1}/{retries}...")
            except RequestException as e:
                logging.error(f"Request failed: {e}")
                break  # Stop retrying on non-retryable errors

            attempt += 1

        return None  # Failed after retries

    def get(self, endpoint: str, params=None, headers=None):
        """GET request wrapper."""
        return self.request("GET", endpoint, params=params, headers=headers)

    def post(self, endpoint: str, data=None, headers=None):
        """POST request wrapper."""
        return self.request("POST", endpoint, data=data, headers=headers)

    def put(self, endpoint: str, data=None, headers=None):
        """PUT request wrapper."""
        return self.request("PUT", endpoint, data=data, headers=headers)

    def delete(self, endpoint: str, headers=None):
        """DELETE request wrapper."""
        return self.request("DELETE", endpoint, headers=headers)
