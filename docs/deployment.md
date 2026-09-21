# Deployment

Set `WELLNESS_API_KEY_ENCODING` to the URL-encoded data.go.kr service key and
set `PORT` to the listening port. The managed `DATABASE_URL` must be available.
Publishing applies the development schema for `wellness_mcp_cache` and
`wellness_mcp_rate_limits` to the production database.

The idempotent schema definition is tracked in `docs/shared_state_schema.sql`.
Apply it to a new development database before starting the server. Startup
checks that both required tables exist and fails clearly if they do not.

Supported entry points:

```bash
python main.py
python -m mcp_server
visitkorea-wellness-mcp
```

The first command remains available for existing Replit workflow and deployment
configuration. Package entry points require an editable or normal installation.