# PCIbex Local Server

A self-hosted application for managing and running PCIbex experiments. The Angular management UI talks to a Quart backend; MongoDB stores user and experiment metadata, while experiment assets and participant results are stored on the filesystem.

The repository contains the application source and development tooling. A packaged release is a deployment artifact, not a source checkout.

## Project layout

- `src/` — Angular 19 management application.
- `server/src/pcibex_server/` — Quart API and PCIbex experiment runtime.
- `server/tests/` — backend tests.
- `server/.env.example` — template for local backend configuration.
- `ibex/` — optional local experiment data directory; it is ignored by Git and may not exist in a fresh checkout.
- `proxy.conf.json` — Angular development proxy for PCIbex runtime routes.
- `deployment/build-release.sh` — builds and verifies a versioned release archive.
- `deployment/install-release.py` and `deployment/verify-release.py` — release installation and archive validation.
- `deployment/tests/` — tests for the release installer and verifier.
- `.github/workflows/backend-tests.yml` — CI, release-artifact build, and tagged GitHub Release publishing.

## Requirements

- Node.js 22.14.0 for the frontend and CI workflow.
- Python 3.11 or newer for backend development and tests. Python 3.12 is used by the release-artifact workflow.
- A running MongoDB instance and a database user configured for the backend.
- Chrome or Chromium for the browser-based tests.

Angular CLI is installed through the project dependencies; a global Angular CLI installation is not required.

## Local development

Run commands from the repository root unless a step says otherwise.

### Configure and install

Install the locked frontend dependencies:

```bash
npm ci
```

Create the local backend environment file:

```bash
cp server/.env.example server/.env
```

Edit `server/.env` with the MongoDB connection settings, `MOSAIC_ADMIN`, `MOSAIC_ADMIN_PASSWORD`, and a strong `JWT_SECRET_KEY`. Keep this file private and never commit it.

Create a backend virtual environment and install the locked test dependencies, build tools, and package:

```bash
python3.11 -m venv server/.venv
source server/.venv/bin/activate
python -m pip install -r server/requirements-test.lock
python -m pip install -r server/build-requirements.lock
python -m pip install --no-build-isolation --no-deps -e server
python -m playwright install chromium
```

The backend creates the configured admin user on startup only if that username does not already exist; changing `MOSAIC_ADMIN_PASSWORD` later does not reset an existing account.

`PCIBEX_DATA_DIR` selects the local experiment-data root. If it is unset, the backend uses the repository’s `ibex/` directory when present; otherwise it uses `$XDG_DATA_HOME/pcibex/ibex`, or `~/.local/share/pcibex/ibex` when `XDG_DATA_HOME` is unset. Set an absolute path explicitly when you want a specific data location. Experiment files, results, and server state are not part of the release archive.

### Run the application

Ensure MongoDB is running and its host, port, database, username, and password match `server/.env`. In one terminal, from the repository root, start the backend:

```bash
source server/.venv/bin/activate
cd server
hypercorn pcibex_server.server:app --bind 127.0.0.1:3001 --reload
```

The backend health endpoint is `http://127.0.0.1:3001/healthz`.

In another terminal, from the repository root, start the Angular development server:

```bash
npm start
```

Open `http://localhost:4200`. The development frontend calls the management API at `http://localhost:3001/api`; `proxy.conf.json` forwards PCIbex runtime routes such as `/www`, the include directories, and `/send` to the backend. The local CORS origins are configured in `server/.env.example`.

### Tests and builds

Run the Angular tests and production frontend build from the repository root:

```bash
npm test -- --watch=false --browsers=ChromeHeadless
npm run build:production
```

Run backend tests from `server/` with the backend virtual environment active:

```bash
cd server
source .venv/bin/activate
python -m unittest discover -s tests -v
```

Run installer and archive-verifier tests from the repository root:

```bash
python -m unittest discover -s deployment/tests -v
```

## Release artifacts

GitHub Actions runs backend and frontend tests, builds the production frontend and backend wheel, verifies the release archive, and uploads the artifact. Pushing a `v*` tag publishes the verified archive, checksum, installer, and verifier as a GitHub Release. CI does not deploy to a server.

To build a release locally, use Python 3.12 and install the build dependencies:

```bash
python3.12 -m venv /tmp/pcibex-build-venv
source /tmp/pcibex-build-venv/bin/activate
python -m pip install -r server/build-requirements.lock
npm ci
./deployment/build-release.sh
```

By default, artifacts are written to `dist/release/`: a `pcibex-release-<commit>.tar.gz` archive, its `.sha256` checksum, `install-release.py`, and `verify-release.py`. The build script verifies the archive before publishing those files. The archive contains the production frontend build, backend wheel, and locked runtime wheels; it excludes local `.env` files, experiment data, tests, and virtual environments. Debugging and development should use the repository source, not the minified frontend bundle.

## Server installation

The installer accepts a release archive and its checksum. Run `python3.12 deployment/install-release.py --help` for all options. Defaults are `/opt/pcibex` for the install root, `pcibex.service` for the systemd unit, and `http://127.0.0.1:3001/healthz` for the health check.

Before using it, an operator must provision the host-specific MongoDB instance, persistent data directory, protected environment file, systemd service, and web-server configuration. The installer only manages versioned application releases: it installs the backend from the bundled wheelhouse, atomically switches the `current` symlink, restarts the configured service, and checks `/healthz`. It does not configure MongoDB, Nginx, systemd, secrets, or experiment-data storage, and it does not perform a MongoDB upgrade.

The first packaged release has no earlier packaged version for automatic rollback. Back up an existing installation and its configuration separately before migrating it to the versioned layout. Later releases can roll back to a retained packaged commit with:

```bash
python3.12 deployment/install-release.py --rollback-to <commit>
```

Replace `<commit>` with the release commit identifier. Keep the systemd service, environment file, MongoDB data, and PCIbex experiment data outside `/opt/pcibex/releases/`.
