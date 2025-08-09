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
        backend="curl_cffi",
        proxies_list=proxies_list,
        max_retries=3,
        impersonate="safari17",   # puedes cambiar a chrome124, etc.
        timeout=25.0
    )
    s.set_headers({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    })

    r = s.get("https://httpbin.org/get", params={"via": "curl_cffi"})
    print("GET status:", getattr(r, "status_code", None))
    print("GET body:", (r.text[:200] + "...") if r else None)

    r = s.put("https://httpbin.org/put", json={"ping": True})
    print("PUT status:", getattr(r, "status_code", None))
    print("Cookies:", s.get_cookies())

if __name__ == "__main__":
    main()
