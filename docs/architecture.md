# Architecture

The server uses a `src` package layout. The composition root creates one checked
settings object, one shared HTTP client, one KTO client, one application service,
and one FastMCP server.

Request flow:

```text
Streamable HTTP request
→ FastMCP schema validation
→ tool registry adapter
→ WellnessService
→ WellnessClient
→ PostgreSQL shared cache and coordination
→ KTO Wellness Tourism API
→ normalized structured result
```

Public MCP interfaces remain in `tools/registry.py`. Domain operations use
ordinary Python values and remain independent of JSON RPC and HTTP transport
details.

PostgreSQL stores expiring upstream responses, coordinates per-key advisory
locks, and atomically counts rate-limit requests. All server instances use the
same state.