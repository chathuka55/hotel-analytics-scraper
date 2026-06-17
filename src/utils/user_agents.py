"""User-Agent rotation utilities to avoid detection."""

import random
from functools import lru_cache
from typing import Optional

from fake_useragent import UserAgent

# Fallback user agents in case fake_useragent fails
FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

# Mobile user agents for mobile simulation
MOBILE_USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]


class UserAgentRotator:
    """Rotates user agents to avoid detection patterns."""

    def __init__(self, use_fake_ua: bool = True):
        self._ua: Optional[UserAgent] = None
        self._use_fake = use_fake_ua
        self._used_agents: list[str] = []

        if use_fake_ua:
            try:
                self._ua = UserAgent(fallback=FALLBACK_USER_AGENTS[0])
            except Exception:
                self._ua = None

    def get_random(self, mobile: bool = False) -> str:
        """Get a random user agent string.

        Args:
            mobile: Whether to return a mobile user agent

        Returns:
            Random user agent string
        """
        if mobile:
            return random.choice(MOBILE_USER_AGENTS)

        if self._ua and self._use_fake:
            try:
                ua = self._ua.random
                self._used_agents.append(ua)
                return ua
            except Exception:
                pass

        ua = random.choice(FALLBACK_USER_AGENTS)
        self._used_agents.append(ua)
        return ua

    def get_chrome(self) -> str:
        """Get a Chrome user agent."""
        chrome_agents = [ua for ua in FALLBACK_USER_AGENTS if "Chrome" in ua and "Edg" not in ua]
        return random.choice(chrome_agents) if chrome_agents else self.get_random()

    def get_firefox(self) -> str:
        """Get a Firefox user agent."""
        firefox_agents = [ua for ua in FALLBACK_USER_AGENTS if "Firefox" in ua]
        return random.choice(firefox_agents) if firefox_agents else self.get_random()

    def get_safari(self) -> str:
        """Get a Safari user agent."""
        safari_agents = [ua for ua in FALLBACK_USER_AGENTS if "Safari" in ua and "Chrome" not in ua]
        return random.choice(safari_agents) if safari_agents else self.get_random()

    def get_usage_stats(self) -> dict:
        """Get statistics on used user agents."""
        if not self._used_agents:
            return {}

        stats = {}
        for ua in self._used_agents:
            # Extract browser name
            if "Chrome" in ua and "Edg" not in ua:
                browser = "Chrome"
            elif "Firefox" in ua:
                browser = "Firefox"
            elif "Safari" in ua and "Chrome" not in ua:
                browser = "Safari"
            elif "Edg" in ua:
                browser = "Edge"
            else:
                browser = "Other"
            stats[browser] = stats.get(browser, 0) + 1
        return stats


@lru_cache()
def get_ua_rotator() -> UserAgentRotator:
    """Get cached user agent rotator."""
    return UserAgentRotator()


def get_random_user_agent(mobile: bool = False) -> str:
    """Quick helper to get a random user agent."""
    return get_ua_rotator().get_random(mobile=mobile)
