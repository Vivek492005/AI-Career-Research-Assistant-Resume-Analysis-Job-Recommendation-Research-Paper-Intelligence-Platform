# Troubleshooting Render deploys

Field notes from running Study Buddy on Render's free tier. The
reference configuration is `render.yaml` in the repository root —
if your service was created by hand in the dashboard, compare it
against that file first; most deploy failures are drift from it.

## 1. Deploy crashes immediately with a SyntaxError

**Symptom.** Build succeeds, then the service crashes on boot with a
`SyntaxError` in application code that runs fine locally.

**Cause.** Render picked a different Python than the project needs
(3.12). The codebase uses syntax that older interpreters reject —
a 3.10 runtime once crashed every deploy this way.

**Fix.** Pin the interpreter. `render.yaml` sets
`PYTHON_VERSION=3.12.0` as an env var; if you manage the service in
the dashboard instead, set the same variable under
**Environment → Environment Variables**, then redeploy.

## 2. Build fails while installing dependencies

**Symptom.** `pip install` fails during the build — commonly a hash
mismatch, or resolution errors around the small `deprecated`
package (a transitive dependency whose releases have broken
unpinned installs before).

**Cause.** Installing from the loose `requirements.in` lets the
resolver pick whatever is newest today, including broken releases.

**Fix.** Always build from the compiled lockfile, exactly as
`render.yaml` does:

```bash
pip install --require-hashes -r requirements.txt
```

If you changed dependencies, regenerate the lockfile locally with
`uv pip compile --generate-hashes` and commit the result — never
hand-edit pins inside `requirements.txt`.

## 3. The app cannot connect to the database

**Symptom.** Boot logs show `sqlalchemy.exc.OperationalError` or the
app starts but every page that touches the DB returns 500.

**Cause.** `DATABASE_URL` is missing, points at the *external*
database URL from another region, or the Postgres add-on was
deleted/recreated so the URL changed.

**Fix.** Let Render inject the URL: in `render.yaml` it comes from
`fromDatabase`, and dashboard setups should copy the **Internal
Database URL** (same region = no egress cost, lower latency). The
app already upgrades the legacy `postgres://` scheme to
`postgresql://` itself, and the `psycopg` driver ships as a binary
wheel in the lockfile — no system packages are needed.

## 4. Boot fails fast over SECRET_KEY

**Symptom.** The process exits during startup with a `RuntimeError`
about `SECRET_KEY` before binding the port.

**Cause.** In production the app refuses to run with the built-in
development `SECRET_KEY` — session cookies signed with a public key
would be forgeable.

**Fix.** Set a real secret. `render.yaml` uses
`generateValue: true` so Render creates one; in the dashboard, set
`SECRET_KEY` to a long random string (32+ characters). Pick once and
keep it: rotating it invalidates every signed-in session.

## 5. First request after idle is very slow — or a POST returns 500

**Symptom.** After ~15 minutes without traffic, the first hit takes
up to a minute, and occasionally the first form submit after a wake
fails with a 500. Retrying works.

**Cause.** Free web services spin down when idle; the first request
pays the cold start (container + interpreter + app boot) and a
request that raced the boot can fail.

**Fix.** For users: just retry — the service is awake now. For
operators: keep `healthCheckPath: /healthz` set (it is in
`render.yaml`) so Render only routes traffic once the app answers,
and upgrade the instance type if cold starts are unacceptable —
they are a free-tier property, not an app bug.

## 6. First deploy logs "relation already exists" table errors

**Symptom.** On a brand-new database, the two gunicorn workers race
to create tables at boot and one logs a duplicate-relation error.

**Cause.** Schema creation runs at application start; with
`--workers 2` both workers can attempt it in the same second.

**Fix.** Restart the service — creation is idempotent, so the second
boot is clean. Avoid triggering two deploys at once. If you run the
app elsewhere with several workers, create the schema once (start a
single worker first) before scaling out.
