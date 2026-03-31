# PCIbex Self-Hosted Platform

A self-hosted alternative to PCIbex Farm for running and managing PCIbex experiments locally, with data stored fully on-premise using MongoDB.

This project consists of two components in a single repository:

- **Frontend** — Angular 19 application
- **Backend** — Quartz application served via Hypercorn

---

## Prerequisites

Before getting started, ensure you have the following installed:

| Tool              | Version      |
| ----------------- | ------------ |
| Node.js           | v22.14.0     |
| Angular CLI       | v19.2.7      |
| Python            | _(see link)_ |
| MongoDB Community | 8.0.9        |

> 📎 Follow the installation guides here: _(add your links here)_

---

## Main Project Structure

```
project-root/
├── ibex/              # Subdirectory containing PCIbex files
├── server/            # Quartz application for backend
├── src/               # Angular 19 application for frontend
├── package.json       # Frontend application package information and executable commands
├── proxy.conf.json    # Configuration file to handle all REST API requests coming from PCIbex experiments
└── README.md
```

---

## Running Locally

### 1. Clone the Repository

```bash
git clone https://github.com/NiranjanHegde26/PCIbex-Based-Server.git
cd PCIbex-Based-Server
```

### 2. Configure Environment Variables

Go to `server/` subdirectory, and copy the file contents of env.example on to a new file called .env.

```bash
cp .env.example .env
```

Populate the configuration values into this file. These configurations depend on the way your MongoDB environment, and you can freely choose the appropriate values for MOSAIC_ADMIN, MOSAIC_ADMIN_PASSWORD and JWT_SECRET_KEY.

> ⚠️ Never commit your `.env` file to version control.

### 3. Configure Backend Variables

Go to `server/` subdirectory, and modify the variables to suit your requirements.

### 4. Install application dependencies

For the frontend dependencies, go to the project root and run,

```bash
npm install
```

Create a virtual environment before installing the backend dependencies using,

```bash
python -m venv venv             # In this case, venv is the name of the virtual environment
source venv/bin/activate        # Windows: venv\Scripts\activate
```

Later, go to `server/` and run:

```bash
pip install -r requirements.txt
```

### 5. Start the Backend

From the `server/` subdirectory, run:

```bash
hypercorn server:app --bind 127.0.0.1:3001 --reload
```

The backend will be available at `http://127.0.0.1:3001`.

### 6. Configure the Frontend Variables

Go to `src/environments/environment.development.ts` and edit the confiugration (only if your frontend and backend run in a different port, or to add a new role to the application)

### 7. Start the Frontend

From the project root, run:

```bash
npm start
```

> This uses the local configuration profile as defined in `package.json`.

The frontend will be available at `http://localhost:4200`.

### 8. You're all set!

Once both the backend and frontend are running, open your browser and navigate to the Angular app URL. You should be able to create, manage, and obtain URLs of PCIbex experiments entirely in your local MongoDB instance.

---

## Deployment

Except for Steps 5 and 7, the rest from [Running Locally](#Running-Locally) apply on your server as well. Complete those first, then follow the additional steps below.

> ⚠️ The following section assumes that the codebase is hosted on a Linux-based server. For Windows-based servers, we recommend referring to different documentations.

### 1. Configure Nginx

A sample Nginx config is provided in the repository at `deployment/ngnix-example`. Copy it to your Nginx config directory and update the placeholders:

```bash
cp deployment/ngnix-example /etc/nginx/sites-available/vd-pcibex
# Edit the file to set your domain/IP, cert files and static file paths

sudo nginx -t && sudo systemctl reload nginx
```

### 2. Set Up the Quartz Backend Service

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

### 3. Deploy frontend

Go to project root, and run:

```bash
.\ui-deploy.sh
```

> Note: Ensure that ui-deploy.sh is executable by running `chmod +x ui-deploy.sh` first.

This shell script automatically builds the Angular frontend code, and copies the dist contents to `/var/www/vd-pcibex`.
