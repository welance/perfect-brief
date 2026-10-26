# Official MCP Registry entry

`server.json` describes the free, bring-your-own-model Perfect Brief server for
the [official MCP Registry](https://registry.modelcontextprotocol.io).

To publish a new version:

1. Production `https://briefs.welance.com/mcp` serves the BYO tools (this
   release deployed) — `curl -s https://briefs.welance.com/v1/byo/status`.
2. Set `version` to the deployed service version.
3. Prove the `com.welance` namespace (owner of `welance.com`; welance.com
   serves the public record at `/.well-known/mcp-registry-auth`, the private
   key is in 1Password, DevOps, "mcp-registry welance.com publisher key"):
   ```bash
   mcp-publisher login http --domain welance.com --private-key <ed25519-hex>
   ```
4. Run `mcp-publisher publish` from this directory.

A remote-only entry needs no package. Registry validation is not a security
review or a listing in Claude, ChatGPT, Cursor or VS Code directories; those
are separate submissions.
