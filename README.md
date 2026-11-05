# PCIbex Self-Hosted Platform

A self-hosted alternative to PCIbex Farm for running and managing PCIbex experiments locally, with data stored fully on-premise using MongoDB.

This project consists of two components in a single repository:

- **Frontend** — Angular 19 application
- **Backend** — Quart application served via Hypercorn

---

## Prerequisites

Before getting started, ensure you have the following installed:

| Tool              | Version  |
| ----------------- | -------- |
| Node.js           | v22.14.0 |
| Angular CLI       | v19.2.7  |
| Python            | 3.11.9   |
| MongoDB Community | 8.0.9    |

> 📎 Follow the installation guides here: Node.js[https://nodejs.org/en/download], Angular[https://angular.dev/installation], MongoDB[https://www.mongodb.com/docs/manual/installation/]

---

## Main Project Structure

```
project-root/
├── deployment/        # Release packaging helper and Linux server examples
├── ibex/              # Subdirectory containing PCIbex files
├── server/            # Quart backend package
├── src/               # Angular 19 application for frontend
├── package.json       # Frontend application package information and executable commands
├── proxy.conf.json    # Configuration file to handle all REST API requests coming from PCIbex experiments
└── README.md
```

---

## Running Locally

### 1. Clone the Repository

```bash
git clone https://github.com/NiranjanHegde26/pcibex-local-server.git
cd pcibex-local-server
```

### 2. Configure Environment Variables

From the repository root, copy the backend environment template:

```bash
cp server/.env.example server/.env
```

Set the MongoDB connection values, `MOSAIC_ADMIN`, `MOSAIC_ADMIN_PASSWORD`, and a strong `JWT_SECRET_KEY`. For local development, leave `PCIBEX_DATA_DIR` empty to use the repository's `ibex/` directory. Production services should set an explicit Linux data directory and public URL in their service environment.

> ⚠️ Never commit your `.env` file to version control.

### 3. Configure Backend Variables

Backend runtime settings are environment variables; see `server/.env.example`. Do not edit host-specific paths into Python source.

### 4. Install application dependencies

From the repository root, install the locked frontend dependencies:

```bash
npm ci
```

Create a Linux virtual environment and install the backend package with its test extras:

```bash
cd server
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-test.lock
python -m pip install --no-deps -e .
python -m playwright install chromium
```
The runtime-only lock is `requirements.lock`; install it before the package with `python -m pip install -r requirements.lock` and `python -m pip install --no-deps .`.
### 5. Create the experiment source directory

With the default local data directory, run this from `server/`:

```bash
mkdir -p ../ibex/source
```

If `PCIBEX_DATA_DIR` points elsewhere, create a `source/` subdirectory there instead.

### 6. Start the Backend

From the `server/` subdirectory, run:

```bash
hypercorn pcibex_server.server:app --bind 127.0.0.1:3001 --reload
```

The backend will be available at `http://127.0.0.1:3001`.

### 7. Configure the Frontend Variables

The frontend uses `src/environments/environment.development.ts` for local development. Production builds use the same-origin `/api` endpoint configured in `src/environments/environment.ts`.

### 8. Start the Frontend

From the project root (use a new terminal or return there with `cd ..`), run:

```bash
npm start
```

> This uses the local configuration profile as defined in `package.json`.

The frontend will be available at `http://localhost:4200`.

### 9. You're all set!

Once both the backend and frontend are running, open your browser and navigate to the Angular app URL. You should be able to create, manage, and obtain URLs of PCIbex experiments entirely in your local MongoDB instance.

---

## Deployment

CI runs backend and frontend tests, builds the production frontend and backend wheel, verifies release contents, and retains the artifact for the workflow run. Pushing a `v*` tag runs the same gates and publishes the tarball, checksum, and matching deployment tools as a GitHub Release. CI does not connect to production; an operator installs the exact tested artifact on the server.

### 1. Configure Nginx

A sample Nginx config is provided at `deployment/nginx-example`. Copy it to the Linux Nginx configuration directory and update the domain, certificate, and webroot values:

```bash
cp deployment/nginx-example /etc/nginx/sites-available/vd-pcibex
# Edit the file to set your domain/IP, cert files and static file paths

sudo nginx -t && sudo systemctl reload nginx
```

### 2. Set Up the Quart Backend Service

A sample systemd service file is provided at `deployment/quartz-service-example`. Registering it as a service lets you manage the backend with standard `systemctl` commands:

```bash
cp deployment/quartz-service-example /etc/systemd/system/pcibex.service
# Edit the file to set the correct paths and user

sudo systemctl daemon-reload
sudo systemctl enable pcibex
sudo systemctl start pcibex
```

To check the status or restart the backend at any point:

```bash
sudo systemctl status pcibex
sudo systemctl restart pcibex
```

### 3. Build a release artifact

From the repository root, build the production frontend and backend wheel into a release archive:

```bash
npm ci
python3 -m pip install -r server/build-requirements.lock
./deployment/build-release.sh
```
This helper builds the production frontend and a self-contained release archive; it does not connect to or modify a server.

### Versioned release rollout
The systemd example uses `/opt/pcibex/current` for the active version and `/etc/pcibex/production.env` for host configuration. Nginx serves `/opt/pcibex/current/frontend/browser`. Keep MongoDB, the environment file, and all PCIbex data directories outside `/opt/pcibex/releases/`; a release contains only the frontend, backend wheel, locked dependencies, and runtime wheels.

Before first rollout, adapt and validate `deployment/nginx-example` and `deployment/quartz-service-example` for the host, then configure systemd and Nginx to use the paths above. The installer requires `/opt/pcibex/current` to be absent or a symlink; it deliberately refuses to replace a live directory. Migrate an existing installation to a versioned release during a separately backed-up maintenance window before using this installer.

1. Push changes on a feature branch and open a pull request to `master`. Merge only after the CI gates pass.
2. From the approved `master` commit, create and push a version tag. The tag starts the same CI gates and publishes the release only if they all pass:
   ```bash
   git switch master
   git pull --ff-only origin master
   git tag -a v1.2.0 -m "Release v1.2.0"
   git push origin v1.2.0
   ```
3. Back up MongoDB and verify the backup before the maintenance window. Confirm the existing `/etc/pcibex/production.env`, systemd environment file, and persistent data paths are unchanged. The app installer does not upgrade MongoDB or modify experiment data.
4. Download all assets for the tag from the GitHub Release page to a temporary directory on the server. Keep `install-release.py`, `verify-release.py`, the `.tar.gz`, and its `.sha256` file together. Before replacing an existing version, record its commit for rollback:
   ```bash
   printf 'Previous release commit: %s\n' "$(basename "$(readlink -f /opt/pcibex/current)")"
   archives=(pcibex-release-*.tar.gz)
   archive="${archives[0]}"
   sha256sum --check "$archive.sha256"
   sudo python3.12 install-release.py \
     --archive "$archive" \
     --checksum "$archive.sha256"
   ```
   The installer independently checks the archive checksum and contents, installs the backend from the bundled wheelhouse without reaching PyPI, checks that the backend package imports, and stages the release under `/opt/pcibex/releases/<commit>`. It atomically switches `/opt/pcibex/current`, restarts `pcibex.service`, and requires `/healthz` to return ready. On failure, it switches back to the previous release and restarts the service. It does not delete previous releases.
5. After a successful health check, use the public site to smoke-test login, experiment upload/access, and participant result submission. If application-level checks fail, use the recorded commit to restore the retained version:
   ```bash
   sudo python3.12 install-release.py --rollback-to 0123456789abcdef
   ```
   Replace the example commit with the ID recorded before deployment. The rollback switches `current`, restarts the service, and verifies `/healthz`; if that check fails, it restores the version that was active before the rollback attempt. Keep failed versions for diagnosis.
