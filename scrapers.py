# scrapers.py
from __future__ import annotations
import random
import time
from typing import Optional, Dict, Any, Literal

import colorama

try:
    from Libs.init import proxies, logs, max_retries
except Exception:
    proxies, logs, max_retries = [], True, 3

# Impersonate por defecto para curl_cffi
IMPERSONATE_DEFAULT = "chrome99_android"


def _pick_proxy(proxies_list: list[str]) -> Optional[Dict[str, str]]:
    if not proxies_list:
        return None
    raw = random.choice(proxies_list)
    parts = raw.strip().split(":")
    if len(parts) == 2:
        host, port = parts
        auth = None
    elif len(parts) == 4:
        host, port, user, pwd = parts
        auth = f"{user}:{pwd}@"
    else:
        return None

    prefix = f"http://{auth if auth else ''}{host}:{port}"
    return {"http": prefix, "https": prefix}


def _log(enabled: bool, message: str, level: str = "info"):
    if not enabled:
        return
    color = {
        "info": colorama.Fore.CYAN,
        "warn": colorama.Fore.YELLOW,
        "error": colorama.Fore.RED,
    }.get(level.lower(), colorama.Fore.WHITE)
    print(color + message + colorama.Style.RESET_ALL)


class BaseScraper:
    def __init__(self, logs: bool = logs, max_retries: int = max_retries):
        self.logs = logs
        self.max_retries = max_retries

    def set_headers(self, headers: dict):
        raise NotImplementedError

    def get_cookies(self) -> dict:
        raise NotImplementedError

    def get(self, url: str, **kwargs):
        raise NotImplementedError

    def post(self, url: str, data=None, json=None, **kwargs):
        raise NotImplementedError

    def put(self, url: str, data=None, json=None, **kwargs):
        raise NotImplementedError


class RequestsScraper(BaseScraper):
    def __init__(self, logs: bool = logs, max_retries: int = max_retries, proxies_list: list[str] = proxies):
        super().__init__(logs, max_retries)
        import requests
        self.requests = requests
        self.session = requests.Session()
        self._apply_proxy(_pick_proxy(proxies_list))

    def _apply_proxy(self, proxy: Optional[Dict[str, str]]):
        if proxy:
            self.session.proxies.update(proxy)
            _log(self.logs, f"[!] Using proxy: {proxy['http']}", "warn")
        else:
            _log(self.logs, "[!] No proxies found in proxies.txt", "error")

    def set_headers(self, headers: dict):
        self.session.headers.update(headers)
        _log(self.logs, "[+] Headers updated", "info")

    def get_cookies(self) -> dict:
        return self.session.cookies.get_dict()

    def get(self, url: str, **kwargs) -> Optional["requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[GET] {url} (Attempt {attempt + 1})")
                return self.session.get(url, **kwargs)
            except self.requests.RequestException as e:
                _log(self.logs, f"[GET ERROR] {e}", "error")
                time.sleep(1)
        return None

    def post(self, url: str, data=None, json=None, **kwargs) -> Optional["requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[POST] {url} (Attempt {attempt + 1})")
                return self.session.post(url, data=data, json=json, **kwargs)
            except self.requests.RequestException as e:
                _log(self.logs, f"[POST ERROR] {e}", "error")
                time.sleep(1)
        return None

    def put(self, url: str, data=None, json=None, **kwargs) -> Optional["requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[PUT] {url} (Attempt {attempt + 1})")
                return self.session.put(url, data=data, json=json, **kwargs)
            except self.requests.RequestException as e:
                _log(self.logs, f"[PUT ERROR] {e}", "error")
                time.sleep(1)
        return None


class HttpxScraper(BaseScraper):
    def __init__(self, logs: bool = logs, max_retries: int = max_retries, proxies_list: list[str] = proxies, timeout: float = 30.0):
        super().__init__(logs, max_retries)
        import httpx
        self.httpx = httpx
        proxy = _pick_proxy(proxies_list)
        if proxy:
            _log(self.logs, f"[!] Using proxy: {proxy['http']}", "warn")
        else:
            _log(self.logs, "[!] No proxies found in proxies.txt", "error")
        self.client = httpx.Client(
            timeout=timeout,
            proxies=proxy or None,
            headers={}
        )

    def set_headers(self, headers: dict):
        self.client.headers.update(headers)
        _log(self.logs, "[+] Headers updated", "info")

    def get_cookies(self) -> dict:
        return dict(self.client.cookies)

    def get(self, url: str, **kwargs) -> Optional["httpx.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[GET] {url} (Attempt {attempt + 1})")
                return self.client.get(url, **kwargs, cookies=self.client.cookies)
            except self.httpx.RequestError as e:
                _log(self.logs, f"[GET ERROR] {repr(e)}", "error")
                time.sleep(1)
        return None

    def post(self, url: str, data=None, json=None, **kwargs) -> Optional["httpx.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[POST] {url} (Attempt {attempt + 1})")
                return self.client.post(url, data=data, json=json, **kwargs, cookies=self.client.cookies)
            except self.httpx.RequestError as e:
                _log(self.logs, f"[POST ERROR] {repr(e)}", "error")
                time.sleep(1)
        return None

    def put(self, url: str, data=None, json=None, **kwargs) -> Optional["httpx.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[PUT] {url} (Attempt {attempt + 1})")
                return self.client.put(url, data=data, json=json, **kwargs, cookies=self.client.cookies)
            except self.httpx.RequestError as e:
                _log(self.logs, f"[PUT ERROR] {repr(e)}", "error")
                time.sleep(1)
        return None


class CurlCffiScraper(BaseScraper):
    def __init__(
        self,
        logs: bool = logs,
        max_retries: int = max_retries,
        proxies_list: list[str] = proxies,
        impersonate: str = IMPERSONATE_DEFAULT,
        timeout: float = 30.0,
    ):
        super().__init__(logs, max_retries)
        from curl_cffi import requests as cffi_requests
        self.cffi_requests = cffi_requests

        proxy = _pick_proxy(proxies_list)
        if proxy:
            _log(self.logs, f"[!] Using proxy: {proxy['http']}", "warn")
        else:
            _log(self.logs, "[!] No proxies found in proxies.txt", "error")

        self.session = cffi_requests.Session(
            impersonate=impersonate,
            timeout=timeout,
            proxies=proxy or None,
        )

    def set_headers(self, headers: dict):
        self.session.headers.update(headers)
        _log(self.logs, f"[+] Headers updated (impersonate={self.session.impersonate})", "info")

    def get_cookies(self) -> dict:
        return self.session.cookies.get_dict()

    def get(self, url: str, **kwargs) -> Optional["cffi_requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[GET] {url} (Attempt {attempt + 1})")
                return self.session.get(url, **kwargs)
            except self.cffi_requests.RequestsError as e:
                _log(self.logs, f"[GET ERROR] {e}", "error")
                time.sleep(1)
        return None

    def post(self, url: str, data=None, json=None, **kwargs) -> Optional["cffi_requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[POST] {url} (Attempt {attempt + 1})")
                return self.session.post(url, data=data, json=json, **kwargs)
            except self.cffi_requests.RequestsError as e:
                _log(self.logs, f"[POST ERROR] {e}", "error")
                time.sleep(1)
        return None

    def put(self, url: str, data=None, json=None, **kwargs) -> Optional["cffi_requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[PUT] {url} (Attempt {attempt + 1})")
                return self.session.put(url, data=data, json=json, **kwargs)
            except self.cffi_requests.RequestsError as e:
                _log(self.logs, f"[PUT ERROR] {e}", "error")
                time.sleep(1)
        return None

class CloudscraperScraper(BaseScraper):
    def __init__(self, logs: bool = logs, max_retries: int = max_retries, proxies_list: list[str] = proxies, browser: str = "chrome", platform: str = "windows", mobile: bool = False):
        super().__init__(logs, max_retries)
        import cloudscraper
        self.cloudscraper = cloudscraper
        self.session = cloudscraper.create_scraper(browser={"browser": browser, "platform": platform, "mobile": mobile})
        self._apply_proxy(_pick_proxy(proxies_list))

    def _apply_proxy(self, proxy: Optional[Dict[str, str]]):
        if proxy:
            self.session.proxies.update(proxy)
            _log(self.logs, f"[!] Using proxy: {proxy['http']}", "warn")
        else:
            _log(self.logs, "[!] No proxies found in proxies.txt", "error")

    def set_headers(self, headers: dict):
        self.session.headers.update(headers)
        _log(self.logs, "[+] Headers updated", "info")

    def get_cookies(self) -> dict:
        return self.session.cookies.get_dict()

    def get(self, url: str, **kwargs) -> Optional["cloudscraper.requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[GET] {url} (Attempt {attempt + 1})")
                return self.session.get(url, **kwargs)
            except self.cloudscraper.requests.RequestException as e:
                _log(self.logs, f"[GET ERROR] {e}", "error")
                time.sleep(1)
        return None

    def post(self, url: str, data=None, json=None, **kwargs) -> Optional["cloudscraper.requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[POST] {url} (Attempt {attempt + 1})")
                return self.session.post(url, data=data, json=json, **kwargs)
            except self.cloudscraper.requests.RequestException as e:
                _log(self.logs, f"[POST ERROR] {e}", "error")
                time.sleep(1)
        return None

    def put(self, url: str, data=None, json=None, **kwargs) -> Optional["cloudscraper.requests.Response"]:
        for attempt in range(self.max_retries):
            try:
                _log(self.logs, f"[PUT] {url} (Attempt {attempt + 1})")
                return self.session.put(url, data=data, json=json, **kwargs)
            except self.cloudscraper.requests.RequestException as e:
                _log(self.logs, f"[PUT ERROR] {e}", "error")
                time.sleep(1)
        return None


Backend = Literal["requests", "httpx", "curl_cffi", "cloudscraper"]

def get_scraper(
    backend: Backend = "requests",
    **kwargs: Any
) -> BaseScraper:
    """
    Ejemplos:
      s = get_scraper("requests", proxies_list=proxies)
      s = get_scraper("httpx", timeout=20)
      s = get_scraper("curl_cffi", impersonate="safari17")
      s = get_scraper("cloudscraper", browser="chrome", platform="windows")
    """
    if backend == "requests":
        return RequestsScraper(**kwargs)
    if backend == "httpx":
        return HttpxScraper(**kwargs)
    if backend == "curl_cffi":
        return CurlCffiScraper(**kwargs)
    if backend == "cloudscraper":
        return CloudscraperScraper(**kwargs)
    raise ValueError("backend inválido")
