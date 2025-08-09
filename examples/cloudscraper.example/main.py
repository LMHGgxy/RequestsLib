import os, sys
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from scrapers import get_scraper
except Exception:
    print("[!] No se pudo importar 'scrapers'. Coloca scrapers.py en el directorio padre o instala el paquete.")
    raise

def main():
    proxies_list: List[str] = []
    s = get_scraper(
        backend="cloudscraper",
        proxies_list=proxies_list,
        max_retries=3,
        browser="chrome",
        platform="windows",
        mobile=False
    )
    s.set_headers({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*"
    })

    r = s.get("https://httpbin.org/headers")
    print("GET status:", getattr(r, "status_code", None))
    print("GET body:", (r.text[:200] + "...") if r else None)

    r = s.post("https://httpbin.org/post", json={"lib": "cloudscraper"})
    print("POST status:", getattr(r, "status_code", None))
    print("Cookies:", s.get_cookies())

if __name__ == "__main__":
    main()
