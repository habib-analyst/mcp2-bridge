# Agentic OAuth Migration Recipe: Google Workspace MCP servers

> Target audience: anyone building AI agents that will call Google Workspace
> MCP servers (Gmail, Drive, Calendar). Enforcement deadline: **Nov 11, 2026**.

## What is happening

Google is introducing an **agentic classification** for OAuth 2.0 clients.
In the Google Cloud Console, when creating or editing an OAuth 2.0 client ID,
you can designate it for AI agents via the **"Use this client for an AI-powered
agent"** checkbox. This self-declaration marks the client as representing AI
agents that execute actions or retrieve context on behalf of users.

Only OAuth clients marked agentic will be allowed to connect to the upcoming
Google Workspace MCP servers. Requests from unmarked clients will be rejected.

**Official reference:** Google Cloud support doc "Manage OAuth Clients",
section "Configure OAuth Clients for AI Agents":
https://support.google.com/cloud/answer/15549257

## Timeline (as reported Oct 12, 2026; verify against the official doc)

| Date | Milestone |
|---|---|
| Oct 12, 2026 | Agentic toggle becomes available on new and existing OAuth clients in the Cloud Console |
| Nov 11, 2026 | Workspace MCP servers begin rejecting requests from clients without the agentic tag |
| Nov 12, 2026 | Agentic configuration becomes permanent for existing clients; changing it afterwards requires creating a brand-new OAuth Client ID |

## Migration recipe

### 1. Inventory your OAuth clients
List every OAuth 2.0 client ID in each Google Cloud project that an AI agent
touches (directly or via an MCP server). Note which ones also serve
human-interactive traffic.

### 2. Split standard vs agentic traffic
Google's stated best practice: if one application serves both human-driven
features (web/mobile calling REST APIs) and AI-agent workflows, create and
maintain **separate OAuth client IDs** for each workflow:

- **Standard client ID** — human-driven, interactive sessions and direct API integrations.
- **Agentic client ID** — exclusively for AI agents, automated tool execution, and MCP integrations.

Separating them lets Workspace admins apply granular access policies to agents
without touching human user access, and keeps monitoring/audit trails clean.

### 3. Enable the agentic tag (do this before Nov 11)
In the Google Cloud Console: Auth Platform > Clients > select the agentic
client ID > edit > check **"Use this client for an AI-powered agent"** > save.
Allow the usual propagation window (settings can take minutes to hours).

### 4. Re-verify consent and scopes
The agentic tag grants **no additional scopes or privileges**. Your app must
still pass user consent and OAuth app verification as before. Re-run your
consent flow against the new agentic client ID and confirm tokens work.

### 5. Point MCP integrations at the agentic client
Any MCP client configuration that will talk to Google Workspace MCP servers
must use the agentic client ID. (mcp2-bridge's `connect_stdio` covers local
servers; remote Workspace MCP endpoints will carry OAuth via the MCP
authorization flow using your agentic client credentials.)

### 6. Watch for the rejection error after Nov 11
Blocked attempts return an error stating the client is not marked as an AI
agent. If you see it: confirm the tag is set on the exact client ID in the
token request, wait out propagation, and check you are not accidentally using
the standard client ID in agent code paths.

## What I could verify vs what remains Google-side

**Verified (2026-10-13):**
- The agentic checkbox and the separate-client-IDs guidance exist in Google's
  official "Manage OAuth Clients" support doc (linked above).
- The Oct 12 / Nov 11 / Nov 12 timeline is reported by press coverage of the
  rollout (e.g. ASTIG, 2026-10-12); it is not yet mirrored in the support doc
  text fetched on 2026-10-13.

**Not yet verifiable (Google-side, pending launch):**
- The exact console UI location/labels of the toggle (doc describes it, but
  the Workspace MCP server endpoints themselves are "upcoming").
- The exact error string returned for unmarked clients.
- Whether existing MCP-based Workspace integrations (e.g. community Gmail/Drive
  MCP servers using standard OAuth) break on Nov 11 or only the new
  first-party Workspace MCP servers enforce it.

**Recommendation:** complete steps 1-4 before Nov 11 regardless; treat the
Nov 12 permanence cutoff as the hard date after which a wrong classification
costs you a client-ID rotation.
