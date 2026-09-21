# VisitKorea Wellness Tourism MCP Server

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://github.com/leejaew/visitkorea-wellnesstourism-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/leejaew/visitkorea-wellnesstourism-mcp/actions/workflows/tests.yml)
![Transport](https://img.shields.io/badge/MCP-Streamable_HTTP-6366F1)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

VisitKorea Wellness Tourism MCP Server is a stateless Model Context Protocol
service for the Korea Tourism Organization
[`WellnessTursmService`](https://www.data.go.kr/data/15144030/openapi.do). It
exposes nine tools for discovering wellness tourism locations in South Korea
and retrieving their details, images, regional codes, and synchronization data.

The server is intended for MCP clients and services that need structured access
to KTO wellness tourism data over JSON Streamable HTTP. It does not provide
booking, availability, or medical advice.

## Key Features

- Nine MCP tools covering catalog, search, synchronization, detail, and image
  operations
- Search by administrative area, coordinates, radius, or keyword
- Seven wellness themes and nine upstream language codes
- Stateless JSON Streamable HTTP endpoint at `/mcp`
- Shared PostgreSQL response cache and rate limit counters
- PostgreSQL advisory locks to prevent duplicate upstream requests
- Input validation, bounded pagination, and normalized error responses
- Host and origin validation, security headers, and secret redaction
- Developer landing page at `/`

## Tech Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.11 or later |
| MCP framework | MCP Python SDK with FastMCP |
| HTTP application | Starlette |
| ASGI server | Uvicorn |
| Upstream client | HTTPX |
| Shared state | PostgreSQL through asyncpg |
| Build backend | setuptools |
| Tests | Python `unittest` |

Dependency constraints are defined in `pyproject.toml` and mirrored in
`requirements.txt`.

## Architecture

```mermaid
flowchart LR
    Client[MCP client] -->|JSON Streamable HTTP| Transport[Starlette and FastMCP]
    Transport --> Middleware[Security headers and rate limiting]
    Middleware --> Tools[MCP tool registry]
    Tools --> Service[Wellness service]
    Service --> Cache[(PostgreSQL shared state)]
    Service --> KTO[KTO WellnessTursmService]
```

The application creates one HTTP client and one PostgreSQL shared state
dependency at startup. Cache entries and fixed window rate counters are shared
across running instances. Advisory locks serialize cache misses for the same
upstream request.

The server exposes tools only. It does not expose MCP resources or prompts.
See [Architecture](docs/architecture.md), [Capabilities](docs/capabilities.md),
and [Security](docs/security.md) for implementation details.

## MCP Tools

| Tool | Purpose |
| --- | --- |
| `get_legal_district_codes` | List province, city, and district codes |
| `get_wellness_sync_list` | Retrieve records for dataset synchronization |
| `search_wellness_by_area` | Search by administrative area |
| `search_wellness_by_location` | Search within a radius of WGS84 coordinates |
| `search_wellness_by_keyword` | Search by text |
| `get_wellness_common_info` | Retrieve common venue details |
| `get_wellness_intro_info` | Retrieve content type specific details |
| `get_wellness_repeating_info` | Retrieve repeating structured details |
| `get_wellness_images` | Retrieve image URLs and copyright information |

Tool schemas provide argument descriptions, defaults, bounds, and accepted
codes directly to MCP clients. Contract tests protect the public tool names and
schemas.

## Repository Structure

```text
.
├── src/mcp_server/
│   ├── clients/          # KTO client, validation, parsing, and shared state
│   ├── config/           # Environment settings and HTTP configuration
│   ├── errors/           # Application error model
│   ├── observability/    # Logging and secret redaction
│   ├── services/         # Transport independent service layer
│   ├── tools/            # MCP operations and registration
│   ├── transports/       # Streamable HTTP application and middleware
│   ├── main.py           # Dependency composition and process startup
│   └── server.py         # FastMCP server factory
├── tests/                # Unit, integration, contract, and security tests
├── docs/                 # Architecture, deployment, security, and SQL schema
├── static/               # Landing page and favicon
├── main.py               # Compatibility launcher
├── pyproject.toml        # Package metadata and build configuration
└── requirements.txt      # Runtime dependency constraints
```

## Requirements

- Python 3.11 or later
- PostgreSQL
- A URL encoded data.go.kr service key for KTO Service ID `15144030`
- Network access to `https://apis.data.go.kr`

The `psql` command line client is optional but useful for applying the included
schema.

## Environment Variables

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `WELLNESS_API_KEY_ENCODING` | Yes | None | URL encoded data.go.kr service key |
| `DATABASE_URL` | Yes | None | PostgreSQL connection string for shared state |
| `PORT` | No | `8080` | HTTP listening port from 1 through 65535 |
| `WELLNESS_ALLOWED_HOSTS` | No | Localhost entries | Comma separated HTTP host allowlist |
| `WELLNESS_ALLOWED_ORIGINS` | No | Local HTTP origins | Comma separated origin allowlist |
| `REPLIT_DOMAINS` | No | None | Replit supplied host discovery value |
| `REPLIT_DEV_DOMAIN` | No | None | Replit supplied development host |

The application does not load `.env` files. Export variables in the shell or
configure them through the deployment platform.

The data.go.kr encoding key may contain escaped characters such as `%2B` and
`%2F`. Use the provided encoding key without decoding or encoding it again.

## Installation

```bash
git clone https://github.com/leejaew/visitkorea-wellnesstourism-mcp.git
cd visitkorea-wellnesstourism-mcp
python -m pip install -e .
```

An editable installation provides the `visitkorea-wellness-mcp` command and
supports package based entry points.

## Database Setup

Create the shared cache and rate limit tables before starting the application:

```bash
psql "$DATABASE_URL" -f docs/shared_state_schema.sql
```

The SQL file is idempotent. Application startup verifies that both tables
exist, but it does not create or migrate them.

The database stores temporary upstream responses and fixed window request
counters. It does not store KTO API keys or end user profiles.

## Local Development

Set the required variables:

```bash
export WELLNESS_API_KEY_ENCODING="your_url_encoded_data_go_kr_service_key"
export DATABASE_URL="postgresql://user:password@localhost:5432/wellness"
export PORT=8080
```

Apply the database schema, then start the server:

```bash
psql "$DATABASE_URL" -f docs/shared_state_schema.sql
python main.py
```

Available routes:

| URL | Purpose |
| --- | --- |
| `http://localhost:8080/` | Developer landing page |
| `http://localhost:8080/favicon.png` | Landing page icon |
| `http://localhost:8080/mcp` | MCP Streamable HTTP endpoint |

The installed package provides two equivalent entry points:

```bash
python -m mcp_server
visitkorea-wellness-mcp
```

## MCP Client Configuration

Point a Streamable HTTP compatible MCP client at the deployed `/mcp` endpoint:

```json
{
  "mcpServers": {
    "visitkorea-wellnesstourism": {
      "type": "streamable-http",
      "url": "https://your-domain.example/mcp"
    }
  }
}
```

The endpoint does not issue session IDs and does not require client
authentication. Restrict network access or add authentication at the gateway
when the service must not be public.

## Build and Package

Install the standard Python build frontend, then build the source and wheel
distributions:

```bash
python -m pip install build
python -m build
```

Generated packages are written to `dist/`.

## Production Run

A production environment requires the two secrets, the initialized PostgreSQL
schema, and an HTTPS proxy or hosting platform in front of Uvicorn.

```bash
export WELLNESS_API_KEY_ENCODING="your_url_encoded_data_go_kr_service_key"
export DATABASE_URL="postgresql://user:password@database:5432/wellness"
export PORT=8080
visitkorea-wellness-mcp
```

The process binds to `0.0.0.0` and reads the port at startup. The service has no
background worker or persistent local filesystem requirement.

On Replit, use the managed PostgreSQL database and store the KTO key as a
secret. The root `python main.py` entry point remains compatible with Replit
workflows. Replit Publish applies development database schema changes to the
production database.

See [Deployment](docs/deployment.md) for the supported entry points and schema
requirements.

## Testing

Run the complete test suite:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Run the compilation check used by CI:

```bash
PYTHONPATH=src python -m compileall -q src tests main.py
```

PostgreSQL integration tests run when `DATABASE_URL` is available and skip
otherwise. HTTP client integration tests use mocked responses. The suite does
not call the live KTO API.

## Security Notes

- Never commit `WELLNESS_API_KEY_ENCODING`, `DATABASE_URL`, or `.env` files.
- Upstream redirects are disabled so the KTO key is not forwarded to another
  host.
- Logs redact the configured API key and `serviceKey` query values.
- MCP requests are limited to 60 requests per 60 seconds per direct client IP.
- PostgreSQL counters enforce the same rate limit across all instances.
- Host and origin validation reduce DNS rebinding exposure.
- Responses include CSP, frame, content type, and referrer policy headers.
- TLS and client authentication must be provided by the deployment platform or
  gateway when required.

## Troubleshooting

### Startup reports a missing API key

Set `WELLNESS_API_KEY_ENCODING` to the encoding key from data.go.kr. Do not use
the decoded key.

### Startup reports a missing database schema

Confirm that `DATABASE_URL` targets the intended database, then run:

```bash
psql "$DATABASE_URL" -f docs/shared_state_schema.sql
```

### Requests fail host or origin validation

Add the public host and origin to the comma separated allowlists:

```bash
export WELLNESS_ALLOWED_HOSTS="mcp.example.com"
export WELLNESS_ALLOWED_ORIGINS="https://mcp.example.com"
```

### The upstream API returns an authentication error

Confirm that the KTO service request is approved and that the URL encoded key
was not decoded or encoded a second time.

## Known Limitations

- The server exposes read only directory data. It does not provide booking,
  availability, or transactional operations.
- Results depend on the KTO service, quota, coverage, and update schedule.
- Korean data may contain more records or fields than translated datasets.
- Content type IDs differ between Korean and multilingual responses.
- The direct ASGI client address is used for rate limiting. Configure trusted
  proxy behavior at the gateway when deploying behind multiple proxy layers.
- The public MCP endpoint has no built in client authentication.
- The landing page loads fonts and client libraries from external CDNs.

## Contributing

Open an issue before submitting a substantial change. Run the test and
compilation commands before opening a pull request. Do not record live KTO
responses containing credentials in fixtures or logs.

## License

Licensed under the [MIT License](LICENSE).

Tourism data is provided by the Korea Tourism Organization through
data.go.kr. Follow the source data terms and the copyright type attached to each
record.