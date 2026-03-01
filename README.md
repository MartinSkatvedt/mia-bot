# M.I.A. Bot

A Discord bot that tracks member inactivity across your server. For each member it records:

- **Last message** — the last time they sent a message in any channel
- **Last online** — the last time they were seen online (online / idle / dnd)

Data persists in a PostgreSQL database and survives bot restarts.

---

## Commands

| Command | Description |
|---|---|
| `!mia <username>` | Show inactivity report for a member |
| `!mia @mention` | Same, using a Discord mention |

**Example output:**
```
📋 M.I.A. Report for Username
💬 Last message: 3 days, 2 hours ago
🔴 Last online:  1 day, 4 hours ago
```

---

## Setup

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application.
2. Under **Bot**, click **Reset Token** and copy your token.
3. Under **Bot → Privileged Gateway Intents**, enable all three:
   - **Server Members Intent**
   - **Presence Intent**
   - **Message Content Intent**
4. Under **OAuth2 → URL Generator**, select the `bot` scope and the `Send Messages` + `Read Message History` permissions. Use the generated URL to invite the bot to your server.

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your bot token:

```
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://mia:mia_password@db:5432/mia_db
```

> **Never commit `.env` to version control.** It is listed in `.gitignore`.

### 3. Run with Docker Compose

**Option A — build locally:**

```bash
docker compose up --build
```

**Option B — use the pre-built image from GitHub Container Registry:**

Replace the `bot` service in `docker-compose.yml`:

```yaml
  bot:
    image: ghcr.io/<your-github-username>/mia-bot:latest
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped
```

Then run:

```bash
docker compose up
```

To run in the background:

```bash
docker compose up -d
```

To stop:

```bash
docker compose down
```

Data is stored in the `postgres_data` Docker volume and persists across restarts. To wipe all data:

```bash
docker compose down -v
```

---

## Publishing a Release

Pushing a new GitHub release automatically builds and publishes the Docker image to the GitHub Container Registry via the included workflow.

1. Tag a commit and create a release on GitHub (e.g. `v1.0.0`).
2. The workflow builds the image and pushes it to `ghcr.io/<owner>/mia-bot` with tags `1.0.0`, `1.0`, and `latest`.

> **Package visibility** follows your repository's visibility. If your repository is private, the published package will be private by default. You can also manage visibility manually under your GitHub profile → **Packages**.
