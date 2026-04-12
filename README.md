# VisitKorea Wellness Tourism MCP Server

![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP-1.27.0-8B5CF6)
![Transport](https://img.shields.io/badge/transport-Streamable_HTTP_%28JSON%29-6366F1)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An MCP (Model Context Protocol) server that wraps the **Korea Tourism Organization (KTO) Wellness Tourism Open API** (`WellnessTursmService`), exposing 9 structured tools that AI agents — including Claude, Manus AI, and any MCP-compatible client — can call directly via Streamable HTTP. Supports 7 wellness themes and 9 languages.

**Live endpoint:** `https://<your-replit-url>/mcp`

---

## Features

- **Area-based search** — list wellness tourism spots by province, city, or district
- **Location-based search** — find spots within a GPS radius (up to 20 km), with distance sorting
- **Keyword search** — full-text search in Korean, English, and other languages
- **7 wellness theme filters** — Hot spring/Spa, Jjimjilbang, Traditional medicine, Healing meditation, Beauty spa, Nature healing, Other wellness
- **Multilingual support** — 9 languages: Korean, English, Japanese, Simplified/Traditional Chinese, German, French, Spanish, Russian
- **Sync list** — full dataset synchronisation list for building and maintaining local databases
- **Detail records** — common info, intro info (type-specific), repeating structured info, and image galleries
- **9 MCP tools** — one per API operation, with full parameter documentation in docstrings
- **Stateless transport** — every request is self-contained; no session state, no expiry issues
- **Security hardened** — rate limiting (60 req/min per IP), security headers (CSP, X-Frame-Options), API key log redaction

---

## Prerequisites

- Python 3.11+
- A KTO Open API key from [data.go.kr](https://www.data.go.kr/data/15144030/openapi.do) (Service ID: `15144030`)

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/leejaew/visitkorea-wellnesstourism-mcp.git
cd visitkorea-wellnesstourism-mcp
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Obtain your API key

1. Visit [https://www.data.go.kr/data/15144030/openapi.do](https://www.data.go.kr/data/15144030/openapi.do)
2. Sign in or create a 공공데이터포털 account
3. Click **활용신청** (Request API access) for the `WellnessTursmService`
4. After approval (~10 minutes), go to My Page and copy your **일반 인증키 (Encoding)** key

### 4. Set the environment variable

```bash
export WELLNESS_API_KEY_ENCODING="your_url_encoded_key_here"
```

On Replit, add it to **Secrets** (not environment variables) under the key name `WELLNESS_API_KEY_ENCODING`.

> The key from data.go.kr is already URL-encoded (contains `%2B`, `%2F`, etc.). Use that value as-is — do not decode or re-encode it.

### 5. Run the server

```bash
cd artifacts/wellness-mcp
python main.py
```

The server starts on the port specified by the `PORT` environment variable (defaults to `8080`).

| URL | Purpose |
|-----|---------|
| `http://localhost:8080/` | Developer landing page |
| `http://localhost:8080/mcp` | MCP Streamable HTTP endpoint |

---

## Connecting AI Agents

### Manus AI

In Manus AI's connector settings, add a custom MCP server:

| Field | Value |
|-------|-------|
| Type | `streamable-http` |
| URL | `https://<your-replit-url>/mcp` |
| Authentication | None |

### Claude Desktop / Other MCP clients

Paste into your client's MCP configuration:

```json
{
  "mcpServers": {
    "visitkorea-wellnesstourism": {
      "type": "streamable-http",
      "url": "https://<your-replit-url>/mcp"
    }
  }
}
```

Replace the URL with your own deployed endpoint if you forked the repository.

---

## Tool Reference

### Tool 1 — `get_legal_district_codes`

Retrieve legal administrative district (법정동) codes for province/city and district filtering.

**Upstream endpoint:** `GET /ldongCode`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |
| `l_dong_regn_cd` | string | Optional | Province/city code (e.g. `11` = Seoul). Omit to list all provinces. |
| `l_dong_list_yn` | string | Optional | `N` = 시도/시군구 codes (default); `Y` = full 법정동 list |

---

### Tool 2 — `search_wellness_by_area`

List wellness tourism spots filtered by region, content type, and wellness theme.

**Upstream endpoint:** `GET /areaBasedList`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |
| `arrange` | string | Optional | Sort order — `A`/`C`/`D` (no image required); `O`/`Q`/`R` (image required) |
| `content_type_id` | string | Optional | Content type ID (see reference table) |
| `mdfcn_dt` | string | Optional | Modified date filter in YYMMDD format |
| `l_dong_regn_cd` | string | Optional | Province/city code |
| `l_dong_signgu_cd` | string | Optional | District code (requires `l_dong_regn_cd`) |
| `wellness_thema_cd` | string | Optional | Wellness theme code (see reference table) |

---

### Tool 3 — `search_wellness_by_location`

Find wellness spots within a GPS radius of a point in South Korea, sorted by proximity.

**Upstream endpoint:** `GET /locationBasedList`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `map_x` | float | **Required** | GPS longitude (WGS84) e.g. `126.9780` |
| `map_y` | float | **Required** | GPS latitude (WGS84) e.g. `37.5665` |
| `radius` | int | **Required** | Search radius in metres — maximum `20000` |
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `arrange` | string | Optional | `E` = nearest first (no image); `S` = nearest first (image required) |
| `content_type_id` | string | Optional | Content type ID |
| `wellness_thema_cd` | string | Optional | Wellness theme code |

Response includes a `dist` field on each item showing the distance in metres from the search point.

---

### Tool 4 — `search_wellness_by_keyword`

Full-text keyword search across all wellness tourism content.

**Upstream endpoint:** `GET /searchKeyword`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keyword` | string | **Required** | Search term in Korean or English (e.g. `"스파"`, `"spa"`) |
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |
| `arrange` | string | Optional | Sort order |
| `content_type_id` | string | Optional | Content type ID |
| `l_dong_regn_cd` | string | Optional | Province/city code |
| `wellness_thema_cd` | string | Optional | Wellness theme code |

---

### Tool 5 — `get_wellness_sync_list`

Retrieve the full dataset synchronisation list — designed for building and maintaining a local copy of the wellness tourism data.

**Upstream endpoint:** `GET /wellnessTursmSyncList`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |
| `showflag` | string | Optional | `1` = publicly visible records only; `0` = hidden records |
| `mdfcn_dt` | string | Optional | Modified date filter in YYMMDD format |
| `old_content_id` | string | Optional | Delta sync — retrieve records after this content ID |
| `wellness_thema_cd` | string | Optional | Wellness theme code |

Returns the same summary fields as `search_wellness_by_area`, plus `showflag` and `oldContentId`.

---

### Tool 6 — `get_wellness_common_info`

Fetch the complete common detail record for a single venue: title, address, GPS, phone, overview, homepage, copyright type.

**Upstream endpoint:** `GET /detailCommon`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | **Required** | Content ID from a search result (e.g. `"702551"`) |
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |

> The `homepage` field may contain raw HTML anchor tags — extract the URL before displaying.

---

### Tool 7 — `get_wellness_intro_info`

Fetch type-specific introductory details (hours, parking, rest days, capacity, credit card info). Response fields vary by `content_type_id`.

**Upstream endpoint:** `GET /detailIntro`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | **Required** | Content ID |
| `content_type_id` | string | **Required** | Must match the `contentTypeId` from the search result |
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |

For tourist attractions (type `12` / `76`) returns: `accomcount`, `chkcreditcard`, `expagerange`, `expguide`, `infocenter`, `opendate`, `parking`, `restdate`, `useseason`, `usetime`.

---

### Tool 8 — `get_wellness_repeating_info`

Fetch repeating structured info items: entrance fees, facilities, amenities, accessibility features, reservation guidance.

**Upstream endpoint:** `GET /detailInfo`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | **Required** | Content ID |
| `content_type_id` | string | **Required** | Must match the venue's category |
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |

Returns a list of items each with `infoname`, `infotext`, `serialnum`, `fldgubun`. Note: this endpoint returns `contentid` and `contenttypeid` in lowercase (unlike other endpoints which use camelCase).

---

### Tool 9 — `get_wellness_images`

Retrieve all image URLs and copyright types for a specific venue.

**Upstream endpoint:** `GET /detailImage`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | **Required** | Content ID |
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |
| `image_yn` | string | Optional | `Y` = venue photos (default); `N` = food/menu images (restaurants only) |

Returns per image: `orgImage` (~500×333 px), `thumbImage` (~150×100 px), `cpyrhtDivCd`, `imgname`, `serialnum`.

---

## Reference Tables

### Wellness Theme Codes

| Code | English | Korean |
|------|---------|--------|
| `EX050100` | Hot spring / Sauna / Spa | 온천/사우나/스파 |
| `EX050200` | Jjimjilbang (Korean sauna) | 찜질방 |
| `EX050300` | Korean traditional medicine | 한방 체험 |
| `EX050400` | Healing meditation | 힐링 명상 |
| `EX050500` | Beauty spa | 뷰티 스파 |
| `EX050600` | Other wellness | 기타 웰니스 |
| `EX050700` | Nature healing | 자연 치유 |

### Language Codes

| Code | Language |
|------|----------|
| `KOR` | Korean (한국어) — default; most complete dataset |
| `ENG` | English |
| `JPN` | Japanese (日本語) |
| `CHS` | Chinese Simplified (简体中文) |
| `CHT` | Chinese Traditional (繁體中文) |
| `GER` | German (Deutsch) |
| `FRE` | French (Français) |
| `SPN` | Spanish (Español) |
| `RUS` | Russian (Русский) |

### Content Type IDs

`content_type_id` values differ between Korean and multilingual responses.

| Category | Korean (`KOR`) | Multilingual (`ENG`, `JPN`, etc.) |
|----------|---------------|----------------------------------|
| Tourist attraction | `12` | `76` |
| Cultural facility | `14` | `78` |
| Event / festival | `15` | `85` |
| Leisure sports | `28` | `75` |
| Accommodation | `32` | `80` |
| Shopping | `38` | `79` |
| Restaurant | `39` | `82` |
| Travel course | `25` | Korean only |
| Transport | Korean only | `77` |

Most wellness venues are classified as **tourist attraction** (`12` for Korean, `76` for multilingual).

### Province Codes (common)

| Code | Region |
|------|--------|
| `11` | Seoul (서울) |
| `21` | Busan (부산) |
| `22` | Daegu (대구) |
| `23` | Incheon (인천) |
| `31` | Gyeonggi-do (경기) |
| `32` | Gangwon-do (강원) |
| `37` | Gyeongsangbuk-do (경북) |
| `38` | Gyeongsangnam-do (경남) |
| `39` | Jeju Island (제주) |

Use `get_legal_district_codes()` (no parameters) to retrieve all 17 province codes, or pass a province code to get its district (시군구) codes.

---

## Usage Examples

### Find hot spring spas near Busan Station

```python
search_wellness_by_location(
    map_x=129.0319, map_y=35.1148,
    radius=5000,
    wellness_thema_cd="EX050100",
    arrange="E",
    lang_div_cd="ENG"
)
```

### Search for spas in Seoul (English)

```python
search_wellness_by_area(
    l_dong_regn_cd="11",
    wellness_thema_cd="EX050100",
    lang_div_cd="ENG",
    num_of_rows=10
)
```

### Keyword search

```python
search_wellness_by_keyword(keyword="스파", lang_div_cd="KOR", num_of_rows=5)
search_wellness_by_keyword(keyword="spa", lang_div_cd="ENG", num_of_rows=5)
```

### Full venue detail retrieval

```python
# 1. Get common info (address, overview, GPS, phone)
get_wellness_common_info(content_id="702551", lang_div_cd="ENG")

# 2. Get operational details (hours, parking, rest days)
get_wellness_intro_info(content_id="702551", content_type_id="76", lang_div_cd="ENG")

# 3. Get fees and facilities
get_wellness_repeating_info(content_id="702551", content_type_id="76", lang_div_cd="ENG")

# 4. Get photos
get_wellness_images(content_id="702551", lang_div_cd="ENG")
```

---

## Project Structure

```
artifacts/wellness-mcp/
├── main.py                  # Replit entrypoint — Starlette app, rate limiting, security headers, lifespan
├── server.py                # FastMCP server definition with 9 registered tool wrappers
├── api/
│   ├── __init__.py          # Re-exports WellnessClient, WellnessAPIError
│   ├── config.py            # BASE_URL, HTTP timeout constants, shared httpx client factory
│   ├── cache.py             # TTL response cache with per-key stampede locks
│   ├── validation.py        # Allowed-value sets and parameter guard functions
│   ├── parser.py            # WellnessAPIError, JSON/XML response normaliser
│   └── client.py            # WellnessClient — async httpx client with 9 API methods
├── tools/
│   ├── __init__.py          # Re-exports all 9 tool functions
│   ├── catalog.py           # get_legal_district_codes, get_wellness_sync_list
│   ├── search.py            # search_wellness_by_area/location/keyword
│   └── detail.py            # get_wellness_common/intro/repeating_info, get_wellness_images
├── static/
│   ├── index.html           # Developer landing page
│   └── favicon.png          # Server icon
├── requirements.txt
├── MANUS_INSTRUCTIONS.md    # Detailed usage guide for Manus AI agents
├── README.md
└── LICENSE
```

---

## Dependencies

```
mcp[cli]>=1.0.0      # MCP SDK (tested with 1.27.0)
httpx>=0.27.0        # Async HTTP client for upstream API calls (tested with 0.28.1)
starlette>=0.37.0    # ASGI framework for routing and middleware (tested with 1.0.0)
uvicorn>=0.29.0      # ASGI server (tested with 0.44.0)
uvloop>=0.19.0       # Optional: faster event loop (tested with 0.22.1; falls back gracefully)
```

---

## Transport & Protocol Notes

This server uses **MCP Streamable HTTP** transport with two non-default settings:

| Setting | Value | Reason |
|---------|-------|--------|
| `json_response` | `True` | Clients such as Manus AI send `Accept: application/json` only. SSE/streaming mode requires both `application/json` and `text/event-stream` in the `Accept` header and returns HTTP 406 otherwise. JSON mode removes this requirement. |
| `stateless_http` | `True` | Gateway-style clients enumerate tools at connector setup time and execute tool calls much later. Stateful sessions are lost whenever the server restarts, causing "Session not found" errors. Stateless mode makes every request fully self-contained — no session IDs are issued or required. |

The server is compatible with any MCP 2025-03-26 client that sends `Accept: application/json`.

---

## Security

| Feature | Details |
|---------|---------|
| Rate limiting | 60 requests per 60 seconds per IP on `/mcp`; returns HTTP 429 with `Retry-After` |
| Security headers | `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` |
| API key redaction | `serviceKey=` is replaced with `[REDACTED]` in all uvicorn access and error logs |
| Cache stampede protection | Per-key `asyncio.Lock` prevents multiple concurrent upstream calls for the same request |

---

## Important Usage Notes

| Note | Detail |
|------|--------|
| **`content_type_id` differs by language** | Tourist attractions are `12` for `KOR` but `76` for `ENG`/`JPN`/etc. Using the wrong ID returns empty results, not an error. |
| **GPS radius hard limit** | `radius` for `search_wellness_by_location` must not exceed `20000` metres. |
| **District code dependency** | `l_dong_signgu_cd` is ignored by the API unless `l_dong_regn_cd` is also provided. |
| **`content_type_id` is required** | Both `get_wellness_intro_info` and `get_wellness_repeating_info` require `content_type_id`. Always read it from the search result and pass it through. |
| **Homepage field may contain HTML** | The `homepage` field from `get_wellness_common_info` sometimes contains raw `<a href="...">` tags. Extract the URL before displaying. |
| **Korean data is most complete** | Multilingual datasets may have fewer records or missing fields. If English returns no results, retry with `lang_div_cd="KOR"`. |
| **Pagination** | Default `num_of_rows` is 10. Increase to 50–100 for broader searches. Use `totalCount` with `pageNo` to traverse multiple pages. |

---

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request. Ensure all changes are tested against the live API and that no API keys are committed to the repository.

---

## License

MIT License — © 2026 leejaew. See [LICENSE](LICENSE) for full text.

Tourism data provided by the Korea Tourism Organization (KTO) via the 공공데이터포털 open API platform. Data usage is subject to KTO terms — attribution is required for `Type1` content; `Type3` content additionally prohibits modification.
