# Clearance ERP MCP server

Standalone stdio server implementing MCP-style JSON-RPC tools used by Clearance:

| Tool | Purpose |
| --- | --- |
| `erp_create_bill` | Create AP bill after validation / HITL |
| `erp_flag_anomaly` | Record fraud/policy anomaly |
| `erp_list_bills` | List session bills |

## Run

```bash
python server.py
```

Send newline-delimited JSON-RPC on stdin, e.g.:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"erp_create_bill","arguments":{"vendor_name":"ACME","invoice_number":"1","total":10}}}
```

Tool contracts match `GET /api/tools` on the Clearance API.

## Wire into Clearance API

```bash
# Windows PowerShell
$env:CLEARANCE_ERP="mcp"
uvicorn app.main:app --port 8000
```

With `CLEARANCE_ERP=mcp`, the API spawns this process and calls tools over JSON-RPC stdio
(`erp_create_bill`, `erp_flag_anomaly`, `erp_list_bills`). Health reports `"erp": "mcp"`.

Default remains in-process mock (`CLEARANCE_ERP=mock`) for CI and free demos.

**Anthropic lesson:** tool descriptions state *when* to use each tool and hard boundaries (never create bills before validation/HITL).
