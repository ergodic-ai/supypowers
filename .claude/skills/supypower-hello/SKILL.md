---
name: supypower-hello
description: >-
  Run Hello functions via supypowers CLI. Available: say hi. Use when the user needs hello functionality.
---

# Hello

Execute tools: `supypowers run <script>:<function> '<json>'`

Output: `{"ok": true, "data": ...}` on success, `{"ok": false, "error": "..."}` on failure.

### hello:hello

Say hi.

```bash
supypowers run hello:hello '{"name": "..."}'
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes |  |
