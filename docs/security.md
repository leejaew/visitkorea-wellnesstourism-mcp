# Security

- DNS rebinding protection validates allowed Host and Origin values.
- Input bounds are enforced in MCP schemas and again in the KTO client.
- Upstream redirects are disabled to avoid forwarding the API key.
- Error responses and logs do not expose request URLs, API keys, or tracebacks.
- The shared response cache expires records and excludes `serviceKey` from keys.
- Atomic shared rate counters apply to the `/mcp` endpoint across instances.

The API is read-only and intentionally public, so no user authentication or
authorization layer is currently required.