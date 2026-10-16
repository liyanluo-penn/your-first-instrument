# Session 7: protected notes and private assignment deadlines

The assignment has two repositories:

- Instructor's template exercise: https://github.com/liyanluo-penn/your-protected-notes
- Personal show-and-tell extension: https://github.com/liyanluo-penn/your-first-instrument

The protected-notes repository was created using GitHub's template mechanism, not as a fork. The countdown project adds the same ownership idea to saved assignments.

## This deployment (2026-10-15)

| Connector | Deployed MCP endpoint |
|---|---|
| `assignment-deadlines` | `https://your-first-instrument-a84r.onrender.com/mcp` |
| `protected-notes` | `https://your-protected-notes-0voz.onrender.com/mcp` |

Both services run on Render's free plan and use the existing `my-memory` Neon
project with Managed Better Auth. The countdown code is merged into `main`.
The project `.mcp.json` contains both endpoints. They are also installed in the
local Claude Code configuration for this project; `claude mcp list` reports
both as Connected. This confirms MCP connectivity, not a Claude account login.

Completed checks: 20 automated tests; live guest writes and reads in a new MCP
session; completion and history; invalid-token rejection; a real user-completed
Neon Auth login; private writes and reads in both services; exclusion from guest
lists; guest rejection when completing a private deadline; session refresh.
Only verification-created rows were removed after the live checks. Two distinct
signed-in users were tested locally with signed JWTs, not with two live accounts.

## Neon

Reuse the earlier memory project's Neon project if available. Enable Managed Better Auth and copy its base URL from Auth → Configuration. Copy the Postgres connection URL from Connect. The new `assignment_deadlines` table is created automatically on first use, alongside any existing course tables.

| Environment variable | Value |
|---|---|
| `DATABASE_URL` | Your secret Neon Postgres connection string. |
| `NEON_AUTH_BASE_URL` | Your Neon Managed Better Auth URL. |
| `PUBLIC_URL` | This particular Render service's HTTPS origin, without `/mcp`. |

Use the same Neon project for both services if desired, with a different `PUBLIC_URL` for each service. Keep all passwords, tokens and connection strings in environment settings or an ignored `.env` file.

## Render

Deploy each repository using New → Blueprint and its `render.yaml`, on the free plan. Set the three variables above. If a service already exists, update its build command and environment to match the repository before redeploying. A Blueprint file does not automatically reconfigure an independently created Web Service.

The countdown service's build command is:

```text
pip install "mcp[cli]>=1.2,<2" "psycopg[binary]>=3.1" "PyJWT[crypto]>=2.8"
```

Start command: `python server.py`. Health check: `/health`. MCP endpoint: `https://YOUR-SERVICE.onrender.com/mcp`. Free instances can take about a minute to wake.

## Claude

In Claude's connector settings, add each deployed `/mcp` URL. For private data choose **Sign in now** and **Register automatically (DCR)** even if Claude detects that sign-in is optional. The server allows guests deliberately. Complete sign-in personally, then call `user_status` before saving private information.

Claude Code is also accepted by the assignment:

```text
claude mcp add --transport http --scope project assignment-deadlines https://YOUR-SERVICE.onrender.com/mcp
```

Use `/mcp` in Claude Code to authenticate. Project configuration can store the server URL; do not place access tokens in a committed `.mcp.json`.

On this computer, open this project in Claude Code and complete Claude's own
login if prompted. Use `/mcp` to sign into each course connector using the
assignment account you created. The one-time verification login did not store
its tokens in Claude. Always call `user_status` and confirm `user` before saving
private information. No Claude account password or assignment password belongs
in a chat message or repository file.

## Verification

```text
uv run python -m unittest discover -s tests -v
```

The dev dependency `pgserver` runs a temporary local Postgres database for tests. No Neon account or real user credentials are needed for the local suite. On this Windows computer, the prepared alternative is `.venv-win\Scripts\python.exe -m unittest discover -s tests -v`.

For the deployed services, verify guest access, a real signed-in user, another user who cannot see the first user's data, and rejection of an invalid token. Check that data survives a new client session or server restart. Local tests are not evidence that deployment or a real Neon login has completed.
