import os, sys, json
from typing import List

# Intenta importar `scrapers` desde el directorio padre
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from scrapers import get_scraper
except Exception as e:
    print("[!] No se pudo importar 'scrapers'. Coloca scrapers.py en el directorio padre o instala el paquete.")
    raise

def main():
    proxies_list: List[str] = [
        # "127.0.0.1:8080",
        # "user:pass@10.0.0.5:3128"
    ]
    s = get_scraper(
        backend="requests",
        proxies_list=proxies_list,
        max_retries=3
    )
    s.set_headers({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)",
        "Accept": "application/json, text/plain, */*"
    })

    # GET con params
    r = s.get("https://httpbin.org/get", params={"q": "demo-requests"})
    print("GET status:", getattr(r, "status_code", None))
    print("GET body:", (r.text[:200] + "...") if r else None)

    # POST JSON
    r = s.post("https://httpbin.org/post", json={"hola": "mundo"})
    print("POST status:", getattr(r, "status_code", None))
    try:
        print("POST json:", r.json())
    except Exception:
        print("POST body:", getattr(r, "text", None))

    # Cookies
    print("Cookies de sesión:", s.get_cookies())

if __name__ == "__main__":
    main()
