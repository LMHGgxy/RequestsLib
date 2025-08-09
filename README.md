# scrapers.py — Mini framework de scraping con `requests`, `httpx`, `curl_cffi` y `cloudscraper`

Pequeña librería que unifica una interfaz común para cuatro backends de HTTP en Python — **requests**, **httpx**, **curl_cffi** y **cloudscraper** — con soporte para:
- Sesiones persistentes y cookies.
- Rotación/sorteo de proxies (con o sin autenticación).
- Retries simples con backoff fijo.
- Logging con colores vía `colorama`.
- *Impersonation* opcional (solo `curl_cffi`) para imitar navegadores reales.
- Emulación de navegador vía **cloudscraper** para sortear desafíos de Cloudflare (cuando aplique).

> **TL;DR**
> ```py
> from scrapers import get_scraper
> s = get_scraper("cloudscraper", proxies_list=["1.1.1.1:3128"])
> r = s.get("https://httpbin.org/headers")
> print(r.status_code, r.text)
> ```

---

## Tabla de contenidos
- [Instalación](#instalación)
- [Quickstart](#quickstart)
- [Conceptos clave](#conceptos-clave)
- [API](#api)
  - [Factory `get_scraper`](#factory-get_scraper)
  - [Clase base `BaseScraper`](#clase-base-basescraper)
  - [Backends](#backends)
    - [`RequestsScraper`](#requestsscraper)
    - [`HttpxScraper`](#httpxscraper)
    - [`CurlCffiScraper`](#curlcffiscraper)
    - [`CloudscraperScraper`](#cloudscraperscraper)
- [Proxies](#proxies)
- [Headers y Cookies](#headers-y-cookies)
- [Retries y Timeouts](#retries-y-timeouts)
- [Ejemplos prácticos](#ejemplos-prácticos)
- [Buenas prácticas](#buenas-prácticas)
- [Solución de problemas](#solución-de-problemas)
- [Licencia](#licencia)
- [Changelog](#changelog)

---

## Instalación

Requisitos mínimos:
- Python 3.10+
- Dependencias:
  - `colorama`
  - `requests` (para el backend *requests*)
  - `httpx` (para el backend *httpx*)
  - `curl_cffi` (para el backend *curl_cffi*)
  - `cloudscraper` (para el backend *cloudscraper*)

Instala las dependencias según tu backend preferido:

```bash
# Todos los backends
pip install colorama requests httpx curl_cffi cloudscraper

# o por backend
pip install colorama requests                 # solo RequestsScraper
pip install colorama httpx                    # solo HttpxScraper
pip install colorama curl_cffi               # solo CurlCffiScraper
pip install colorama cloudscraper            # solo CloudscraperScraper
```

Estructura prevista del proyecto (opcional):
```
.
├── scrapers.py
└── Libs/
    └── init.py  # (opcional) define: proxies, logs, max_retries
```

> Si `Libs/init.py` no existe, la librería usa por defecto:
> `proxies=[]`, `logs=True`, `max_retries=3`.

---

## Quickstart

```py
from scrapers import get_scraper

# 1) Elige backend: "requests" | "httpx" | "curl_cffi" | "cloudscraper"
s = get_scraper(
    backend="cloudscraper",
    proxies_list=["127.0.0.1:8080", "user:pass@10.0.0.5:3128"],
    max_retries=5
)

# 2) Ajusta headers comunes
s.set_headers({
    "User-Agent": "Mozilla/5.0 ...",
    "Accept": "application/json, text/plain, */*"
})

# 3) Haz requests
r = s.get("https://httpbin.org/get", params={"q": "hola"})
print(r.status_code, r.text)

# 4) POST JSON
r = s.post("https://httpbin.org/post", json={"hola": "mundo"})
print(r.status_code, r.json())

# 5) Cookies de la sesión
print(s.get_cookies())
```

---

## Conceptos clave

- **Sesiones**: cada backend mantiene su propia sesión (cookies persistentes entre llamadas).
- **Proxies**: se toma 1 proxy al azar de `proxies_list`. Soporta:
  - `host:port`
  - `host:port:user:pass` o `user:pass@host:port` (ambos aceptados al pasar `proxies_list`).
- **Logs**: `_log()` colorea mensajes `info`, `warn`, `error` con `colorama`.
- **Retries**: cada método (`get`, `post`, `put`) reintenta hasta `max_retries` con una espera fija de 1s.
- **Impersonation**: solo para `curl_cffi`, usando `impersonate="chrome99_android"` por defecto.
- **Cloudscraper**: usa una sesión compatible con desafíos JS/CF de Cloudflare en ciertos escenarios (no garantiza bypass universal).

---

## API

### Factory `get_scraper`

```py
get_scraper(backend: Literal["requests","httpx","curl_cffi","cloudscraper"] = "requests", **kwargs) -> BaseScraper
```
**Parámetros comunes (`**kwargs`)**:
- `logs: bool = True` — habilita/inhabilita logs.
- `max_retries: int = 3` — número de reintentos.
- `proxies_list: list[str] = []` — lista de proxies para elegir 1 al azar.

**Parámetros específicos**:
- `HttpxScraper`: `timeout: float = 30.0`
- `CurlCffiScraper`: `impersonate: str = "chrome99_android"`, `timeout: float = 30.0`
- `CloudscraperScraper`: `browser: str = "chrome"`, `platform: str = "windows"`, `mobile: bool = False`

**Ejemplos**:
```py
s1 = get_scraper("requests", proxies_list=["host:port"])
s2 = get_scraper("httpx", timeout=20.0)
s3 = get_scraper("curl_cffi", impersonate="safari17")
s4 = get_scraper("cloudscraper", browser="chrome", platform="windows", mobile=False)
```

---

### Clase base `BaseScraper`

Métodos que implementan todos los backends:

- `set_headers(headers: dict) -> None`  
  Actualiza los headers de la sesión.

- `get_cookies() -> dict`  
  Retorna las cookies actuales de la sesión.

- `get(url: str, **kwargs)`  
- `post(url: str, data=None, json=None, **kwargs)`  
- `put(url: str, data=None, json=None, **kwargs)`  
  Envían la solicitud correspondiente usando la sesión. Todos aceptan `**kwargs` propios de cada backend (e.g., `params`, `timeout`, etc.).  
  **Retorno**: objeto `Response` del backend correspondiente o `None` si fallan todos los reintentos.

---

### Backends

#### `RequestsScraper`

- Usa `requests.Session()`.
- `set_headers` → `session.headers.update(...)`.
- `get_cookies` → `session.cookies.get_dict()`.
- Acepta `**kwargs` de `requests` (`params`, `verify`, `timeout`, `allow_redirects`, etc.).
- Proxies: `session.proxies.update({"http": "...","https":"..."})`.

#### `HttpxScraper`

- Usa `httpx.Client(...)`.
- `set_headers` → `client.headers.update(...)`.
- `get_cookies` → `dict(client.cookies)`.
- Acepta `**kwargs` de `httpx` (`params`, `follow_redirects`, `verify`, etc.).
- Proxies: `Client(proxies=proxy)` al construir.

#### `CurlCffiScraper`

- Usa `curl_cffi.requests.Session(...)`.
- `set_headers` → `session.headers.update(...)`.
- `get_cookies` → `session.cookies.get_dict()`.
- Acepta `**kwargs` de `curl_cffi.requests`.
- **Impersonate**: `Session(impersonate="chrome99_android")` por defecto.
- Ventaja: compatibilidad mejorada con algunos *anti-bots* mediante *JA3/HTTP2 fingerprints*.

#### `CloudscraperScraper`

- Usa `cloudscraper.create_scraper(...)` (sobre `requests`).
- `set_headers` → `session.headers.update(...)`.
- `get_cookies` → `session.cookies.get_dict()`.
- Acepta `**kwargs` compatibles con `requests`.
- **Opciones de navegador**: `browser`, `platform`, `mobile` afectan la emulación del cliente.
- Nota: Cloudscraper no es un bypass garantizado para todas las protecciones; úsalo como una opción más del toolkit.

---

## Proxies

Formato admitido en `proxies_list`:
- `host:port`  
- `host:port:user:pass` (la librería lo convierte a `user:pass@host:port` internamente)

La librería convierte automáticamente a:
```py
{"http": "http://user:pass@host:port", "https": "http://user:pass@host:port"}
```

> **Nota**: Si no se proveen proxies, verás el log `"[!] No proxies found in proxies.txt"` y la sesión se crea **sin** proxy.

Ejemplo:
```py
proxies = ["190.10.10.10:8080", "user123:pw456@45.5.6.7:3128"]
s = get_scraper("httpx", proxies_list=proxies)
```

---

## Headers y Cookies

```py
s.set_headers({
    "User-Agent": "Mozilla/5.0 ...",
    "Accept-Language": "es-PE,es;q=0.9"
})

print(s.get_cookies())      # dict de cookies actuales
r = s.get("https://httpbin.org/cookies/set?x=1")
print(s.get_cookies())      # ahora incluye {"x": "1"}
```

---

## Retries y Timeouts

- **Retries**: cada request reintenta hasta `max_retries` si ocurre una excepción del backend. Hay una espera fija de `1s` entre intentos.
- **Timeouts**:
  - `RequestsScraper`: pásalo por `**kwargs` (`timeout=15`).
  - `HttpxScraper`: define `timeout` en el constructor o en cada llamada.
  - `CurlCffiScraper`: define `timeout` en el constructor o en cada llamada.
  - `CloudscraperScraper`: igual que `requests` (por llamada con `timeout=...`).

Ejemplo:
```py
s = get_scraper("requests", max_retries=5)
r = s.get("https://example.com", timeout=20)
```

---

## Ejemplos prácticos

### 1) Cloudscraper con configuración de navegador

```py
s = get_scraper(
    "cloudscraper",
    proxies_list=["user:pass@proxy.acme.com:3128"],
    max_retries=4,
    browser="chrome",
    platform="windows",
    mobile=False
)
s.set_headers({"Accept": "application/json"})
r = s.get("https://api.example.com/data", params={"page": 1})
if r and r.status_code == 200:
    data = r.json()
```

### 2) Enviar formulario con `requests`

```py
s = get_scraper("requests")
payload = {"user": "alice", "pwd": "123456"}
r = s.post("https://target.example/login", data=payload)
```

### 3) `curl_cffi` con *impersonate* específico

```py
s = get_scraper("curl_cffi", impersonate="safari17", proxies_list=[])
s.set_headers({"User-Agent": "Mozilla/5.0 ..."})
r = s.get("https://botdetection.example/")
```

### 4) Reutilizar cookies entre llamadas

```py
s = get_scraper("httpx")
s.get("https://httpbin.org/cookies/set?session=abc")
print(s.get_cookies()["session"])  # "abc"
```

---

## Buenas prácticas

- **Fija un `User-Agent` realista** si el destino es sensible.
- **Gestiona proxies fallidos**: si un proxy cae, recrea el scraper con otro proxy.
- **Añade backoff exponencial** si tu caso lo requiere (este repo usa 1s fijo para simplicidad).
- **Manejo de errores**: valida `r is not None` y el `status_code` antes de asumir éxito.
- **Respeta Términos de Uso** de los sitios objetivo.

---

## Solución de problemas

- *“`No proxies found in proxies.txt`”*  
  → Proporciona `proxies_list=[...]` o ignora si no necesitas proxy.

- *`ModuleNotFoundError` (requests/httpx/curl_cffi/cloudscraper)*  
  → Instala la dependencia del backend que vas a usar.

- *Timeouts frecuentes*  
  → Aumenta `timeout`, revisa el proxy, o disminuye concurrencia externa.

- *Bloqueos por anti-bot*  
  → Prueba `curl_cffi` con `impersonate` distinto (e.g., `chrome124`, `safari17`) o usa `cloudscraper`.
  → Considera rotación de IPs/UA y pausas aleatorias.

---

## Licencia

MIT. Úsalo bajo tu propia responsabilidad y respeta la legalidad vigente.

---

## Changelog

- **v0.2.0** — Se añade backend **CloudscraperScraper** y documentación asociada.
- **v0.1.0** — Versión inicial con `requests`, `httpx` y `curl_cffi`.
