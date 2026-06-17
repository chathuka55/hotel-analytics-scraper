"""HTTP session management with retry, proxy, and UA support."""

from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config.settings import get_settings
from src.monitoring.logger import get_logger
from src.utils.proxies import ProxyRotator
from src.utils.user_agents import get_random_user_agent

logger = get_logger(__name__)

# Retry strategy for urllib3
URLLIB3_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
    raise_on_status=False,
)


def create_session(
    proxy_rotator: Optional[ProxyRotator] = None,
    custom_headers: Optional[Dict[str, str]] = None,
    use_random_ua: bool = True,
    max_retries: int = 3,
) -> requests.Session:
    """Create a configured requests session.

    Args:
        proxy_rotator: Optional proxy rotator for proxy support
        custom_headers: Additional headers to include
        use_random_ua: Whether to use a random user agent
        max_retries: Number of retries for failed connections

    Returns:
        Configured requests Session
    """
    session = requests.Session()

    # Set up retry adapter
    adapter = HTTPAdapter(
        max_retries=Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        ),
        pool_connections=10,
        pool_maxsize=10,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set default headers
    headers = {
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }

    # Set user agent
    if use_random_ua:
        headers["User-Agent"] = get_random_user_agent()

    # Merge custom headers
    if custom_headers:
        headers.update(custom_headers)

    session.headers.update(headers)

    # Set proxy if available
    if proxy_rotator and proxy_rotator.has_proxies:
        proxy_dict = proxy_rotator.get_proxy_dict()
        if proxy_dict:
            session.proxies.update(proxy_dict)
            logger.debug(f"Using proxy: {proxy_dict}")

    return session


class SessionManager:
    """Manages HTTP sessions with automatic retry, proxy, and UA rotation."""

    def __init__(
        self,
        proxy_rotator: Optional[ProxyRotator] = None,
        use_random_ua: bool = True,
        max_retries: int = 3,
    ):
        """Initialize session manager.

        Args:
            proxy_rotator: Proxy rotation handler
            use_random_ua: Whether to rotate user agents
            max_retries: Max retries per request
        """
        self._proxy_rotator = proxy_rotator
        self._use_random_ua = use_random_ua
        self._max_retries = max_retries
        self._session: Optional[requests.Session] = None
        self._request_count = 0

    @property
    def session(self) -> requests.Session:
        """Get or create the session."""
        if self._session is None:
            self._session = self._create_session()
        return self._session

    def _create_session(self) -> requests.Session:
        """Create a fresh session."""
        return create_session(
            proxy_rotator=self._proxy_rotator,
            use_random_ua=self._use_random_ua,
            max_retries=self._max_retries,
        )

    def refresh_session(self) -> requests.Session:
        """Create a new session (useful after blocks)."""
        if self._session:
            self._session.close()
        self._session = self._create_session()
        logger.debug("Session refreshed with new UA and proxy")
        return self._session

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> requests.Response:
        """Make a GET request.

        Args:
            url: URL to request
            headers: Optional extra headers
            timeout: Request timeout
            **kwargs: Additional requests arguments

        Returns:
            Response object
        """
        settings = get_settings()
        timeout = timeout or settings.scraping.request_timeout

        merged_headers = {}
        if self._use_random_ua:
            merged_headers["User-Agent"] = get_random_user_agent()
        if headers:
            merged_headers.update(headers)

        self._request_count += 1
        return self.session.get(
            url, headers=merged_headers, timeout=timeout, **kwargs
        )

    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> requests.Response:
        """Make a POST request.

        Args:
            url: URL to request
            data: Form data
            json: JSON body
            headers: Optional extra headers
            timeout: Request timeout
            **kwargs: Additional requests arguments

        Returns:
            Response object
        """
        settings = get_settings()
        timeout = timeout or settings.scraping.request_timeout

        merged_headers = {}
        if self._use_random_ua:
            merged_headers["User-Agent"] = get_random_user_agent()
        if headers:
            merged_headers.update(headers)

        self._request_count += 1
        return self.session.post(
            url, data=data, json=json, headers=merged_headers,
            timeout=timeout, **kwargs,
        )

    def close(self) -> None:
        """Close the session."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def request_count(self) -> int:
        """Total requests made with this manager."""
        return self._request_count
