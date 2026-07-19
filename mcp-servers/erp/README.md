# Clearance ERP MCP server (sketch)

Phase 1 implements ERP tools **in-process** (`apps/api/app/services/erp.py`) with MCP-compatible tool descriptors exposed at `GET /api/tools`.

## Planned standalone server

```text
tools:
  - erp_create_bill
  - erp_list_bills
```

Run pattern (future):

```bash
# example shape — wire to official MCP Python SDK when promoting to Phase 2
python server.py
```

**Tool design lesson (Anthropic):** descriptions must state *when* to use the tool and hard boundaries (e.g. only after validation / human approval). Bad tool docs poison multi-agent systems.
