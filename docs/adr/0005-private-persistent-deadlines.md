# ADR-0005: Give saved assignment deadlines an owner

- Date: 2026-10-15
- Status: Implemented locally; deployment verification pending
- Context: Liyan selected the existing deadline-countdown project for Session 7's show-and-tell extension. Implementation and tests were prepared with Codex assistance.

## Decision

Keep the existing clock and countdown tools. Add `save_deadline`, `list_deadlines`, `complete_deadline`, and `user_status` with Neon Postgres persistence and Neon Auth identity.

Ownership is the verified JWT `sub`, never an email or a model-supplied user id. Every read and update includes `user_id IS NOT DISTINCT FROM %s`; signed-in callers get private lists and guests share a clearly labeled demonstration list. Missing credentials mean guest. Malformed, expired, forged, or wrong-issuer credentials fail before any database write. An explicitly chosen `guest-no-shelf` credential retains the template's guest demonstration.

Use a new `assignment_deadlines` table. The old countdown tool stored nothing, so no old rows need migration or reassignment. Other course tables are untouched. Completing an assignment changes a flag and preserves history. Save timezone-aware timestamps as `TIMESTAMPTZ`; reject missing timezones and recalculate countdowns when listing.

Reuse the instructor's MIT-licensed OAuth bridge, preserving attribution in `NOTICE` and `LICENSE-auth.txt`. Add mandatory S256 PKCE, registered redirect validation, and authorization-code binding to the client and redirect. These checks prevent the bridge from accepting incomplete or mismatched authorization requests.

## Alternatives considered

- Local JSON or SQLite: simple, but Render's ephemeral filesystem cannot guarantee that saved deadlines survive redeployment.
- Email as owner: readable, but changing an email would separate someone from their existing assignments.
- Treat invalid credentials as guest: hides login failures and risks publishing a deadline intended to be private.
- Refuse all guests: useful for a production private planner, but prevents the assignment's guest-versus-user demonstration. Guest responses and tool descriptions explicitly identify the shared list.
- Delete completed rows: loses useful assignment history. A completion flag preserves it.

## Verification and limitations

The suite uses a real temporary Postgres database, real Ed25519 signatures and an HTTP JWKS endpoint. It checks isolated guest/Alice/Bob lists, cross-owner update rejection, persistence across connections, changed emails, invalid inputs, expired/forged tokens, and OAuth request binding. The existing countdown tests remain.

The inherited OAuth bridge keeps client registrations and in-flight codes in memory. Restarting the service can require reconnecting Claude; deadline data remains in Postgres. This is a single-instance course prototype. Live Neon login and Render deployment must also be verified before claiming the online assignment is complete.
