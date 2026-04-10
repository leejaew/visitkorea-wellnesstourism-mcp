# VisitKorea Wellness Tourism MCP Server

An MCP (Model Context Protocol) server that wraps the **Korea Tourism Organization (KTO) Wellness Tourism Open API** (`WellnessTursmService`), exposing 9 structured tools that AI agents — including Claude and Manus AI — can call directly via Server-Sent Events (SSE). Supports 7 wellness themes and 9 languages.

## Features

- **Area-based search** — list wellness tourism spots by province, city, or district
- **Location-based search** — find spots within a GPS radius (up to 20 km), with distance sorting
- **Keyword search** — full-text search in Korean, English, and other languages
- **7 wellness theme filters** — Hot spring/Spa, Jjimjilbang, Traditional medicine, Healing meditation, Beauty spa, Nature healing, Other wellness
- **Multilingual support** — 9 languages: Korean, English, Japanese, Simplified/Traditional Chinese, German, French, Spanish, Russian
- **Sync list** — full dataset synchronisation list for building and maintaining local databases
- **Detail records** — common info, intro info (type-specific), repeating structured info, and image galleries
- **9 MCP tools** — one per API operation, with full parameter documentation in docstrings

## Prerequisites

- Python 3.11+
- A KTO Open API key from [data.go.kr](https://www.data.go.kr/data/15144030/openapi.do) (Service ID: `15144030`)
- Replit account (for deployment)

## Installation & Replit Secrets Setup

1. **Clone or fork this repository** into your Replit account.
2. **Obtain your API key** by registering at [https://www.data.go.kr/data/15144030/openapi.do](https://www.data.go.kr/data/15144030/openapi.do).
3. **Set Replit Secrets** — open the Secrets tab in Replit and add:

   | Secret name | Description |
   |-------------|-------------|
   | `WELLNESS_API_KEY_ENCODING` | URL-encoded key — used as `serviceKey` in all API requests |
   | `WELLNESS_API_KEY_DECODING` | Raw decoded key — stored for reference |

4. **Install dependencies** (Replit handles this automatically):
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the server**:
   ```bash
   python main.py
   ```

The server starts on the `PORT` environment variable (default `8080`).
- Landing page: `http://localhost:8080/`
- SSE endpoint: `http://localhost:8080/sse`

## MCP Connector JSON

Paste this into your AI agent's custom connector settings (Claude Desktop, Manus AI, or any MCP-compatible client):

```json
{
  "mcpServers": {
    "visitkorea-wellnesstourism": {
      "type": "sse",
      "url": "https://visitkorea-wellnesstourism-mcp.replit.app/sse",
      "description": "VisitKorea Wellness Tourism MCP — search and retrieve Korean wellness tourism data (spas, jjimjilbang, healing meditation, traditional medicine, nature therapy, beauty spas) from the Korea Tourism Organization"
    }
  }
}
```

Replace the URL with your deployed Replit project URL.

## Tool Reference

### Tool 1 — `get_legal_district_codes`

Retrieve legal administrative district (법정동) codes for province/city and district filtering.

**Endpoint:** `GET /ldongCode`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lang_div_cd` | string | Optional | Language code (default: `KOR`) |
| `num_of_rows` | int | Optional | Results per page (default: 10) |
| `page_no` | int | Optional | Page number (default: 1) |
| `l_dong_regn_cd` | string | Optional | Province/city code (e.g. `11` = Seoul) |
| `l_dong_list_yn` | string | Optional | `N` = 시도/시군구 codes; `Y` = full 법정동 list |

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/ldongCode?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=KOR&lDongRegnCd=11&lDongListYn=N&_type=json
```

---

### Tool 2 — `search_wellness_by_area`

List wellness tourism spots filtered by region, content type, and wellness theme.

**Endpoint:** `GET /areaBasedList`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lang_div_cd` | string | Optional | Language code |
| `arrange` | string | Optional | Sort order (A/C/D/O/Q/R) |
| `content_type_id` | string | Optional | Content type ID (see Content Types table) |
| `mdfcn_dt` | string | Optional | Modified date filter (YYMMDD) |
| `l_dong_regn_cd` | string | Optional | Province/city code |
| `l_dong_signgu_cd` | string | Optional | District code (requires `l_dong_regn_cd`) |
| `wellness_thema_cd` | string | Optional | Wellness theme code (see Wellness Themes table) |

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/areaBasedList?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=KOR&contentTypeId=12&arrange=C&_type=json
```

---

### Tool 3 — `search_wellness_by_location`

Find wellness spots within a GPS radius (WGS84 coordinates). Maximum radius: 20,000 m.

**Endpoint:** `GET /locationBasedList`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `map_x` | float | **Required** | GPS longitude (WGS84) |
| `map_y` | float | **Required** | GPS latitude (WGS84) |
| `radius` | int | **Required** | Search radius in metres (max 20,000) |
| `arrange` | string | Optional | Sort: `E`/`S` = distance (this endpoint only); A/C/D/O/Q/R = standard |
| `content_type_id` | string | Optional | Content type ID |
| `wellness_thema_cd` | string | Optional | Wellness theme code |

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/locationBasedList?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=KOR&mapX=126.981611&mapY=37.568477&radius=1000&arrange=E&_type=json
```

---

### Tool 4 — `search_wellness_by_keyword`

Full-text keyword search across all wellness tourism content.

**Endpoint:** `GET /searchKeyword`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `keyword` | string | **Required** | Search keyword (Korean or English; auto URL-encoded) |
| `lang_div_cd` | string | Optional | Language code |
| `arrange` | string | Optional | Sort order |
| `content_type_id` | string | Optional | Content type ID |
| `l_dong_regn_cd` | string | Optional | Province/city code |
| `wellness_thema_cd` | string | Optional | Wellness theme code |

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/searchKeyword?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=KOR&keyword=스파&arrange=C&_type=json
```

---

### Tool 5 — `get_wellness_sync_list`

Retrieve the wellness tourism synchronisation list for building local datasets.

**Endpoint:** `GET /wellnessTursmSyncList`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `showflag` | string | Optional | `1` = publicly visible; `0` = hidden |
| `old_content_id` | string | Optional | Previous content ID for delta sync |
| `mdfcn_dt` | string | Optional | Modified date filter (YYMMDD) |
| `wellness_thema_cd` | string | Optional | Wellness theme code |

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/wellnessTursmSyncList?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=KOR&showflag=1&wellnessThemaCd=EX050500&_type=json
```

---

### Tool 6 — `get_wellness_common_info`

Fetch full common detail record: title, address, GPS, phone, homepage, overview.

**Endpoint:** `GET /detailCommon`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | **Required** | Content ID (e.g. `702551`) |
| `lang_div_cd` | string | Optional | Language code |

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/detailCommon?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=KOR&contentId=702551&_type=json
```

---

### Tool 7 — `get_wellness_intro_info`

Fetch type-specific introductory details. Response fields vary by `content_type_id`.

**Endpoint:** `GET /detailIntro`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | **Required** | Content ID |
| `content_type_id` | string | **Required** | Content type ID — required on this endpoint |
| `lang_div_cd` | string | Optional | Language code |

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/detailIntro?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=KOR&contentId=322850&contentTypeId=12&_type=json
```

---

### Tool 8 — `get_wellness_repeating_info`

Fetch repeating structured info: fees, amenities, accessibility, reservations.

**Endpoint:** `GET /detailInfo`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | **Required** | Content ID |
| `content_type_id` | string | **Required** | Content type ID — required on this endpoint |
| `lang_div_cd` | string | Optional | Language code |

Note: API response field names are all lowercase — `contentid`, `contenttypeid`.

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/detailInfo?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=ENG&contentId=1000306&contentTypeId=76&_type=json
```

---

### Tool 9 — `get_wellness_images`

Retrieve all image URLs and copyright types for a content item.

**Endpoint:** `GET /detailImage`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content_id` | string | **Required** | Content ID |
| `image_yn` | string | Optional | `Y` = general images (default); `N` = food menu images (restaurants only) |
| `lang_div_cd` | string | Optional | Language code |

**Example:**
```
http://apis.data.go.kr/B551011/WellnessTursmService/detailImage?serviceKey=KEY&numOfRows=10&pageNo=1&MobileOS=ETC&MobileApp=WellnessTourismMCP&langDivCd=ENG&contentId=1000306&imageYN=Y&_type=json
```

---

## Wellness Theme Code Reference

| Code | Korean | English |
|------|--------|---------|
| `EX050100` | 온천/사우나/스파 | Hot spring / Sauna / Spa |
| `EX050200` | 찜질방 | Jjimjilbang (Korean sauna) |
| `EX050300` | 한방 체험 | Korean traditional medicine experience |
| `EX050400` | 힐링 명상 | Healing meditation |
| `EX050500` | 뷰티 스파 | Beauty spa |
| `EX050600` | 기타 웰니스 | Other wellness |
| `EX050700` | 자연 치유 | Nature healing |

## Language Code Reference

| Code | Language |
|------|----------|
| `KOR` | Korean (한국어) — default |
| `ENG` | English |
| `JPN` | Japanese (日本語) |
| `CHS` | Chinese Simplified (简体中文) |
| `CHT` | Chinese Traditional (繁體中文) |
| `GER` | German (Deutsch) |
| `FRE` | French (Français) |
| `SPN` | Spanish (Español) |
| `RUS` | Russian (Русский) |

## Content Type IDs

| Category | Korean `contentTypeId` | Multilingual `contentTypeId` |
|----------|----------------------|------------------------------|
| 관광지 (Tourist attraction) | `12` | `76` |
| 문화시설 (Cultural facility) | `14` | `78` |
| 행사/공연/축제 (Event/festival) | `15` | `85` |
| 레포츠 (Leisure sports) | `28` | `75` |
| 숙박 (Accommodation) | `32` | `80` |
| 쇼핑 (Shopping) | `38` | `79` |
| 음식점 (Restaurant) | `39` | `82` |
| 여행코스 (Travel course) | `25` | Korean only |
| 교통 (Transport) | Multilingual only | `77` |

## API Key Registration

1. Visit [https://www.data.go.kr/data/15144030/openapi.do](https://www.data.go.kr/data/15144030/openapi.do)
2. Sign in or create a 공공데이터포털 account
3. Click **활용신청** (Request API access) for service `WellnessTursmService`
4. After approval (~10 minutes), retrieve your **일반 인증키 (Encoding)** key from My Page
5. Add it to Replit Secrets as `WELLNESS_API_KEY_ENCODING`

## Project Structure

```
visitkorea-wellnesstourism-mcp/
├── main.py                  # Replit entrypoint — starts HTTP server + mounts MCP
├── server.py                # MCP server definition and tool registrations
├── api/
│   ├── __init__.py
│   └── wellness_client.py   # Async httpx client wrapping all 9 API calls
├── tools/
│   ├── __init__.py
│   └── wellness_tools.py    # MCP tool function implementations
├── static/
│   └── index.html           # Developer landing page
├── requirements.txt
├── README.md
├── LICENSE
└── .gitignore
```

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request. Ensure all changes are tested against the live API and that no API keys are committed to the repository.

## License

MIT License — © 2026 leejaew. See [LICENSE](LICENSE) for full text.

Tourism data provided by the Korea Tourism Organization (KTO) via the 공공데이터포털 open API platform. Data usage is subject to KTO terms — attribution is required for `Type1` content; `Type3` content additionally prohibits modification.
