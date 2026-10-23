# Official MCP Registry entry — DRAFT

`server.json` describes the free, bring-your-own-model Perfect Brief server for
the [official MCP Registry](https://registry.modelcontextprotocol.io). It is a
**draft**: nothing has been published.

Before publishing:

1. Production `https://briefs.welance.com/mcp` serves the BYO tools (this
   release deployed) — `curl -s https://briefs.welance.com/v1/byo/status`.
2. Set `version` to the deployed service version.
3. Prove the `com.welance` namespace (owner of `welance.com`):
   ```bash
   mcp-publisher login dns --domain welance.com --private-key <ed25519-hex>
   ```
   with the matching `v=MCPv1; k=ed25519; p=<public-key>` TXT record on
   `welance.com`. (HTTP proof via `/.well-known/mcp-registry-auth` also works.)
4. Remove the `"status": "draft"` note and run `mcp-publisher publish` from
   this directory.

A remote-only entry needs no package. Registry validation is not a security
review or a listing in Claude, ChatGPT, Cursor or VS Code directories; those
are separate submissions.
