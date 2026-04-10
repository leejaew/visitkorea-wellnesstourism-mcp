# Manus AI — Instructions for VisitKorea Wellness Tourism MCP

## What This MCP Is

This MCP server provides direct, structured access to the **Korea Tourism Organization (KTO) Wellness Tourism dataset**, officially published on [data.go.kr](https://www.data.go.kr/data/15144030/openapi.do) under the service ID `WellnessTursmService`. The data covers wellness tourism destinations across all of South Korea — spas, hot springs, jjimjilbang (Korean sauna), traditional medicine clinics, healing meditation centres, beauty spas, and nature therapy sites.

The server exposes **9 tools** over Server-Sent Events (SSE). Each tool wraps one API endpoint from the KTO open API, normalises the response, and returns a clean dict. No data is cached or synthesised — every call returns live data from the official KTO dataset.

---

## When to Use This MCP

Activate tools from this MCP whenever the user's request involves any of the following:

- Finding **wellness, spa, sauna, jjimjilbang, hot spring, healing, or traditional medicine** experiences in South Korea
- Recommending or comparing **Korean wellness destinations** by region, proximity, or theme
- Retrieving **operating hours, pricing, facilities, or contact info** for a Korean wellness venue
- Building **itineraries that include wellness stops** in a specific Korean city or district
- Answering questions about **specific wellness tourism venues** by name or content ID
- Fetching **photo galleries** of Korean wellness venues to accompany recommendations
- Any task requiring **official, KTO-sourced wellness data** rather than general web knowledge

Do **not** use this MCP for wellness destinations outside South Korea, general health advice, medical treatment recommendations, or real-time availability/booking — the API provides directory and profile data, not scheduling.

---

## Data Model: How Records Are Structured

Every wellness venue in the dataset has a unique **`contentId`** (e.g. `"702551"`). Most workflows start with a search that returns a list of summary records, and optionally deepen into detail records using that `contentId`.

Each search result includes:
- `contentId` — unique record identifier
- `contentTypeId` — tourism category (see Content Type IDs below)
- `title` — venue name
- `baseAddr` / `detailAddr` — street address
- `mapX` / `mapY` — WGS84 longitude / latitude
- `tel` — phone number
- `orgImage` / `thumbImage` — image URLs (may be empty)
- `wellnessThemaCd` — wellness theme code
- `cpyrhtDivCd` — copyright type (`"Type1"` or `"Type3"`)

Detail tools add: full overview text, homepage URL, operating hours, capacity, fees, amenities, accessibility, and full image galleries.

---

## Reference Tables

### Wellness Theme Codes (`wellness_thema_cd`)

| Code | English | Korean |
|------|---------|--------|
| `EX050100` | Hot spring / Sauna / Spa | 온천/사우나/스파 |
| `EX050200` | Jjimjilbang (Korean sauna) | 찜질방 |
| `EX050300` | Korean traditional medicine | 한방 체험 |
| `EX050400` | Healing meditation | 힐링 명상 |
| `EX050500` | Beauty spa | 뷰티 스파 |
| `EX050600` | Other wellness | 기타 웰니스 |
| `EX050700` | Nature healing | 자연 치유 |

### Language Codes (`lang_div_cd`)

| Code | Language |
|------|---------|
| `KOR` | Korean — default; most complete dataset |
| `ENG` | English |
| `JPN` | Japanese |
| `CHS` | Chinese Simplified |
| `CHT` | Chinese Traditional |
| `GER` | German |
| `FRE` | French |
| `SPN` | Spanish |
| `RUS` | Russian |

> **Important:** Always match `lang_div_cd` to the language the user expects results in. The `contentTypeId` values differ between Korean (`KOR`) and all multilingual responses — use the correct set (see below).

### Content Type IDs (`content_type_id`)

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

> Most wellness venues are classified as **tourist attraction** (`12` for Korean, `76` for multilingual). When in doubt, omit `content_type_id` to search all categories.

### Sort Orders (`arrange`)

| Code | Meaning | Image required? |
|------|---------|----------------|
| `A` | Alphabetical by title | No |
| `C` | Most recently modified | No |
| `D` | Creation date | No |
| `O` | Alphabetical by title | Yes |
| `Q` | Most recently modified | Yes |
| `R` | Creation date | Yes |
| `E` | Distance nearest first | No — location search only |
| `S` | Distance nearest first | Yes — location search only |

---

## Tool Reference and Usage Instructions

### Tool 1 — `get_legal_district_codes`

**Purpose:** Retrieve province/city codes (`lDongRegnCd`) and district codes (`lDongSignguCd`) used as filters in the three search tools.

**When to call it:** Call this tool first whenever the user specifies a Korean region by name (e.g. "in Seoul", "near Busan", "in Gangwon-do") and you do not already know the exact code.

**Key parameters:**
- `l_dong_regn_cd` — leave empty to get all province/city codes; set to a province code (e.g. `"11"`) to get its district codes
- `l_dong_list_yn` — `"N"` (default) returns 시도/시군구 level codes; `"Y"` returns full 법정동 codes

**Common province codes:**

| Code | Region |
|------|--------|
| `11` | Seoul (서울) |
| `21` | Busan (부산) |
| `22` | Daegu (대구) |
| `23` | Incheon (인천) |
| `24` | Gwangju (광주) |
| `25` | Daejeon (대전) |
| `26` | Ulsan (울산) |
| `31` | Gyeonggi-do (경기) |
| `32` | Gangwon-do (강원) |
| `33` | Chungcheongbuk-do (충북) |
| `34` | Chungcheongnam-do (충남) |
| `35` | Jeollabuk-do (전북) |
| `36` | Jeollanam-do (전남) |
| `37` | Gyeongsangbuk-do (경북) |
| `38` | Gyeongsangnam-do (경남) |
| `39` | Jeju Island (제주) |

**Example:** User asks for spa options in Seoul's Gangnam district → call `get_legal_district_codes(l_dong_regn_cd="11")` to get district codes → find Gangnam → pass that district code to the next search tool.

---

### Tool 2 — `search_wellness_by_area`

**Purpose:** List wellness tourism spots filtered by administrative region (province and/or district), wellness theme, and content type. Use when the user wants venues in a specific Korean region.

**When to call it:**
- User asks for wellness venues "in [city/province]"
- User wants to browse by wellness category in a region
- No GPS coordinates are available

**Required parameters:** None — all parameters are optional, but at least one filter is recommended.

**Key parameters:**
- `l_dong_regn_cd` — province/city code from `get_legal_district_codes`
- `l_dong_signgu_cd` — district code (requires `l_dong_regn_cd` to be set)
- `wellness_thema_cd` — filter by wellness theme
- `num_of_rows` — set higher (e.g. `20`) to get more results per call

**Returns:** List of summary records. Each item has `contentId`, `title`, `baseAddr`, `mapX`/`mapY`, `tel`, `orgImage`, `wellnessThemaCd`. Use `contentId` for follow-up detail calls.

---

### Tool 3 — `search_wellness_by_location`

**Purpose:** Find wellness venues within a GPS radius of any point in South Korea, sorted by proximity.

**When to call it:**
- User asks for wellness venues "near me", "near [landmark]", or "within X km of [location]"
- You have GPS coordinates (or can infer them from a landmark/address)

**Required parameters:**
- `map_x` — WGS84 longitude (e.g. `126.9780` for central Seoul)
- `map_y` — WGS84 latitude (e.g. `37.5665` for central Seoul)
- `radius` — search radius in **metres**, maximum `20000` (20 km)

**Key behaviour:**
- Use `arrange="E"` to sort results by distance (nearest first) — this is the most useful sort for proximity queries
- The response includes a `dist` field on each item showing the exact distance in metres from the search centre
- If you do not know the GPS coordinates of a location, look them up before calling this tool

**Example GPS coordinates for common Korean cities:**

| City | Longitude (`map_x`) | Latitude (`map_y`) |
|------|--------------------|--------------------|
| Seoul (centre) | `126.9780` | `37.5665` |
| Busan (centre) | `129.0756` | `35.1796` |
| Jeju City | `126.5312` | `33.4996` |
| Gyeongju | `129.2114` | `35.8562` |
| Jeonju | `127.1480` | `35.8242` |

---

### Tool 4 — `search_wellness_by_keyword`

**Purpose:** Full-text keyword search across all wellness tourism content.

**When to call it:**
- User searches by venue name or partial name
- User uses a descriptive term not covered by theme codes (e.g. "forest bathing", "mud therapy")
- User provides a Korean name directly (e.g. "신라호텔 스파")

**Required parameters:**
- `keyword` — the search term; can be Korean or English; Korean is automatically URL-encoded

**Key advice:**
- For Korean keywords, pass the Korean characters directly — the client handles encoding
- Combine with `wellness_thema_cd` or `l_dong_regn_cd` to narrow results
- If results are too broad, add a theme code filter

---

### Tool 5 — `get_wellness_sync_list`

**Purpose:** Retrieve the full dataset synchronisation list, designed for applications maintaining a local copy of the wellness tourism data.

**When to call it:**
- User asks to see all wellness venues (full catalogue)
- Task requires enumerating the complete dataset across multiple pages
- Checking for recently modified records (`mdfcn_dt` filter)

**Key parameters:**
- `showflag="1"` — returns only publicly visible records (recommended for user-facing results)
- `mdfcn_dt` — YYMMDD format date filter (e.g. `"250101"` for records modified since 1 Jan 2025)
- `old_content_id` — used for delta sync to retrieve records after a specific content ID

**Note:** This tool returns the same summary fields as `search_wellness_by_area`, plus `showflag` and `oldContentId`. Paginate using `page_no` and `num_of_rows` to traverse the full dataset.

---

### Tool 6 — `get_wellness_common_info`

**Purpose:** Retrieve the complete common detail record for a single wellness venue, given its `contentId`.

**When to call it:** Always call this after a search when the user wants full details about a specific venue — address, phone, overview text, GPS, homepage, copyright type.

**Required parameters:**
- `content_id` — the `contentId` from a search result (e.g. `"702551"`)

**Returns:**
- `title`, `baseAddr` + `detailAddr` (full address), `zipCd`, `tel`, `telname`
- `overview` — multi-sentence description of the venue
- `homepage` — may contain raw HTML anchor tags; extract the URL before displaying
- `mapX` / `mapY` — GPS coordinates for mapping
- `cpyrhtDivCd` — `"Type1"` (free use with attribution) or `"Type3"` (no modification allowed)
- `regDt` / `mdfcnDt` — registration and last-modified dates

---

### Tool 7 — `get_wellness_intro_info`

**Purpose:** Retrieve type-specific introductory details for a venue. Response fields vary by `content_type_id`.

**When to call it:** When the user wants operational details: capacity, credit card acceptance, age recommendations, operating hours, open date, parking, rest days, seasons of use.

**Required parameters:**
- `content_id` — venue content ID
- `content_type_id` — **must match** the `contentTypeId` returned in the search result for this venue

**For tourist attractions (type `12` / `76`) returns:**
- `accomcount` — maximum visitor capacity
- `chkcreditcard` — credit card acceptance info
- `expagerange` — recommended age range
- `expguide` — experience guide text
- `infocenter` — information centre phone
- `opendate` — opening date
- `parking` — parking availability
- `restdate` — regular rest/closure days
- `useseason` — recommended seasons
- `usetime` — operating hours

> Other content types (accommodation, restaurant, etc.) return entirely different fields relevant to their category.

---

### Tool 8 — `get_wellness_repeating_info`

**Purpose:** Retrieve repeating structured info items — entrance fees, facility list, amenities, accessibility features, reservation guidance — as a list of named key-value pairs.

**When to call it:** When the user asks about pricing, facilities, accessibility, or reservation procedures for a specific venue.

**Required parameters:**
- `content_id` — venue content ID
- `content_type_id` — must match the venue's category

**Returns:** A list of items, each with:
- `infoname` — the label (e.g. "Admission fee", "Parking", "Reservation")
- `infotext` — the value (e.g. "Adults 15,000 KRW, Children 8,000 KRW")
- `serialnum` — ordering index
- `fldgubun` — field group number

> Note: The API returns `contentid` and `contenttypeid` (all lowercase) on this endpoint, unlike other endpoints which use camelCase.

---

### Tool 9 — `get_wellness_images`

**Purpose:** Retrieve all image URLs and copyright types for a specific wellness venue.

**When to call it:** When the user wants to see photos of a venue, or when building a visual presentation of results.

**Required parameters:**
- `content_id` — venue content ID

**Key parameters:**
- `image_yn="Y"` — general venue photos (default)
- `image_yn="N"` — food/menu images (restaurant venues `39`/`82` only)

**Returns per image:**
- `orgImage` — full-resolution image (~500×333 px)
- `thumbImage` — thumbnail (~150×100 px)
- `cpyrhtDivCd` — `"Type1"` (attribution required) or `"Type3"` (attribution + no modification)
- `imgname` — image filename
- `serialnum` — display order

---

## Standard Workflows

### Workflow A — Region + Theme Search (most common)

1. **`get_legal_district_codes`** → find the province code for the user's target region (skip if you already know the code)
2. **`search_wellness_by_area`** → pass `l_dong_regn_cd`, optionally `wellness_thema_cd`; collect `contentId` values
3. **`get_wellness_common_info`** → for each venue the user wants details on, retrieve full record

### Workflow B — Proximity Search

1. Determine GPS coordinates for the user's location or named landmark
2. **`search_wellness_by_location`** → pass `map_x`, `map_y`, `radius` (≤ 20,000 m), `arrange="E"` for distance order
3. **`get_wellness_common_info`** → retrieve detail for shortlisted venues

### Workflow C — Venue Name Search

1. **`search_wellness_by_keyword`** → pass the venue name or descriptive term as `keyword`
2. **`get_wellness_common_info`** → retrieve detail for the matched venue

### Workflow D — Full Detail Retrieval (for itinerary or deep research)

1. Any search tool → obtain `contentId` and `contentTypeId`
2. **`get_wellness_common_info`** → address, overview, GPS, homepage
3. **`get_wellness_intro_info`** → hours, rest days, capacity, parking
4. **`get_wellness_repeating_info`** → fees, amenities, accessibility
5. **`get_wellness_images`** → photo gallery URLs

---

## Important Constraints and Caveats

| Constraint | Detail |
|-----------|--------|
| **Language code vs. content type ID** | `content_type_id` values differ between `KOR` and other language codes. Tourist attractions are `12` in Korean but `76` in English/Japanese/etc. Using the wrong value returns an empty result, not an error. |
| **GPS radius hard limit** | `radius` for `search_wellness_by_location` must not exceed `20000` metres. The server enforces this and returns an `INVALID_RADIUS` error if exceeded. |
| **Region code dependency** | `l_dong_signgu_cd` (district) is ignored by the API unless `l_dong_regn_cd` (province) is also provided. |
| **`get_wellness_intro_info` requires `content_type_id`** | This is a required field (not optional) on this endpoint. Always read `contentTypeId` from the search result and pass it through. |
| **`get_wellness_repeating_info` requires `content_type_id`** | Same as above — mandatory. |
| **Homepage field may contain HTML** | The `homepage` field from `get_wellness_common_info` sometimes contains raw `<a href="...">` tags. Extract the URL before presenting it. |
| **Copyright type** | `Type1` images and text: free use with attribution to KTO. `Type3` images and text: attribution required and modification prohibited. |
| **Data language completeness** | The `KOR` dataset is the most complete. Multilingual datasets (`ENG`, `JPN`, etc.) may have fewer records or missing fields. If a user wants English results but gets no data, try `KOR` and translate key fields. |
| **Pagination** | Default `num_of_rows` is 10. Increase to 50–100 for broad searches. Use `totalCount` and `pageNo` to determine whether multiple pages exist. |
| **API rate limit** | 1,000 requests/day on the development key. In deployed (production) mode, limits are higher. Batch searches efficiently and avoid redundant calls. |

---

## Example Interaction Patterns

**"Find hot spring spas near Busan station"**
→ `search_wellness_by_location(map_x=129.0319, map_y=35.1148, radius=5000, wellness_thema_cd="EX050100", arrange="E")`
→ For top results: `get_wellness_common_info(content_id=...)`

**"What jjimjilbang are in Jeju Island?"**
→ `search_wellness_by_area(l_dong_regn_cd="39", wellness_thema_cd="EX050200", lang_div_cd="KOR", num_of_rows=20)`

**"Tell me everything about Spa 1899 Donuimun"**
→ `search_wellness_by_keyword(keyword="스파 1899 돈의문")` or `search_wellness_by_keyword(keyword="Spa 1899")`
→ `get_wellness_common_info(content_id=...)` + `get_wellness_intro_info(content_id=..., content_type_id=...)` + `get_wellness_repeating_info(content_id=..., content_type_id=...)`

**"Show me photos of Shinsegae Spa"**
→ `search_wellness_by_keyword(keyword="신세계 스파")` → `get_wellness_images(content_id=...)`

**"Plan a wellness day in Gangnam"**
→ `get_legal_district_codes(l_dong_regn_cd="11")` → find Gangnam district code
→ `search_wellness_by_area(l_dong_regn_cd="11", l_dong_signgu_cd="<gangnam_code>", num_of_rows=20)`
→ `get_wellness_common_info` + `get_wellness_intro_info` for top 3–5 venues
