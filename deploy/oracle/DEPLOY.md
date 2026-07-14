# Deploy Local RAG on Oracle Cloud (Always Free)

This guide takes you from **zero** to a **live, HTTPS, always-free** deployment of
Local RAG on an Oracle Cloud ARM VM. The whole app (backend + frontend) runs on
one small VM behind [Caddy](https://caddyserver.com), which gives you automatic
HTTPS and a single origin (so there are no CORS problems).

**Cost:** $0. Oracle's *Always Free* ARM VMs never expire and your card is only
used for identity verification (it is **not** charged for Always Free resources).

---

## What you'll end up with

```
https://your-app.duckdns.org
        |
     [ Caddy ]  (auto-HTTPS, ports 80/443)
      /      \
 static SPA   /api/*  ->  FastAPI backend  ->  LanceDB + SQLite (persistent volume)
```

---

## Step 1 — Create an Oracle Cloud account

1. Go to <https://www.oracle.com/cloud/free/> and click **Start for free**.
2. Sign up. You'll need:
   - A valid email and phone number.
   - A **credit/debit card for identity verification only** (Always Free resources are never charged).
3. Pick a **Home Region** close to you. ⚠️ This can't be changed later, and your
   Always Free VM must live here. (Regions with more ARM capacity are easier — if
   one region says "out of capacity" in Step 2, that's a known Oracle quirk; retry
   later or try a nearby region at signup.)
4. Finish verification and log in to the **Oracle Cloud Console**.

---

## Step 2 — Create the Always Free ARM VM

1. In the Console, open the menu (☰) → **Compute** → **Instances** → **Create instance**.
2. **Name:** `local-rag`.
3. **Image and shape** → **Edit**:
   - **Image:** Canonical **Ubuntu 22.04** (or 24.04).
   - **Shape:** click **Change shape** → **Ampere** → **VM.Standard.A1.Flex**
     (this is the ARM Always Free shape).
   - Set **OCPUs = 2** and **Memory = 12 GB** (well within the Always Free
     allowance of 4 OCPU / 24 GB). This is plenty for the embedding model.
4. **Networking:** leave the defaults (it creates a VCN). Make sure
   **"Assign a public IPv4 address"** is enabled.
5. **Add SSH keys:**
   - Choose **Generate a key pair for me** and **download both** the private and
     public keys, **or** paste your existing public key.
   - Keep the private key safe — you'll use it to SSH in.
6. Click **Create** and wait until the instance is **Running**. Note its
   **Public IP address** (e.g. `140.238.x.x`).

---

## Step 3 — Open the firewall (ports 80 & 443)

Oracle blocks inbound traffic by default in **two** places. Do both.

### 3a. Security List (cloud firewall)
1. From the instance page, click the **Virtual Cloud Network** link → **Security Lists** → **Default Security List**.
2. **Add Ingress Rules** (add two):
   | Source CIDR | IP Protocol | Destination Port |
   |-------------|-------------|------------------|
   | `0.0.0.0/0` | TCP         | `80`             |
   | `0.0.0.0/0` | TCP         | `443`            |

### 3b. OS firewall (once you're SSH'd in — see Step 4)
Ubuntu on Oracle ships with `iptables` rules. Run:
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

---

## Step 4 — SSH into the VM

From your machine (PowerShell), using the private key you downloaded:
```powershell
# Fix key permissions the first time (Windows):
icacls .\ssh-key.key /inheritance:r
icacls .\ssh-key.key /grant:r "$($env:USERNAME):(R)"

ssh -i .\ssh-key.key ubuntu@<YOUR_PUBLIC_IP>
```
The default user for Ubuntu images is `ubuntu`.

---

## Step 5 — Install Docker on the VM

Run these on the VM:
```bash
sudo apt-get update && sudo apt-get upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # apply the group without logging out
docker version  # sanity check
```

---

## Step 6 — Get a free domain (DuckDNS)

Caddy needs a domain to issue an HTTPS certificate. A free DuckDNS subdomain works great.

1. Go to <https://www.duckdns.org>, sign in (GitHub/Google), and create a subdomain,
   e.g. `your-app` → gives you `your-app.duckdns.org`.
2. In the DuckDNS dashboard, set the subdomain's **IP** to your VM's **Public IP**
   and click **update ip**.
3. Verify it resolves (from your PC): `nslookup your-app.duckdns.org` should show the VM IP.

> Prefer your own domain? Just create an **A record** pointing to the VM IP and use
> that hostname as `DOMAIN` below instead.

---

## Step 7 — Clone the repo and configure

On the VM:
```bash
git clone https://github.com/pigchip/local-rag.git
cd local-rag/deploy/oracle
cp .env.example .env
nano .env
```
Fill in `.env`:
```
DOMAIN=your-app.duckdns.org
TLS_EMAIL=you@example.com
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...        # your Groq key
# (or set NVIDIA_API_KEY / GEMINI_API_KEY / OPENROUTER_API_KEY and change LLM_PROVIDER)
```
Save with `Ctrl+O`, `Enter`, then `Ctrl+X`.

---

## Step 8 — Build and launch

```bash
docker compose up -d --build
```
The first build takes a few minutes (installs Python deps + builds the SPA). Then:

- **Caddy** automatically obtains a Let's Encrypt certificate for your domain.
- **backend** starts on the internal network; data persists in the `rag_data` volume.
- **frontend** builds once, publishes static files to a shared volume, then exits
  (a `Exited (0)` status for the `frontend` container is **normal** — it's a one-shot builder).

Open **https://your-app.duckdns.org** 🎉

Check logs if needed:
```bash
docker compose ps
docker compose logs -f caddy      # watch cert issuance
docker compose logs -f backend
```

---

## Step 9 — Bring over your existing knowledge bases (optional)

Your local KBs live in `backend/data/vector_store/lancedb` on your PC. To copy them
to the VM's persistent volume:

```powershell
# From your PC: copy the lancedb folder up to the VM home dir
scp -i .\ssh-key.key -r `
  C:\Users\aguzmancruz\local-rag\backend\data\vector_store\lancedb `
  ubuntu@<YOUR_PUBLIC_IP>:~/lancedb-import
```
Then on the VM, load it into the running backend's volume:
```bash
# Copy into the named volume via a helper container
# (the volume is named oracle_rag_data — confirm with: docker volume ls)
docker run --rm -v oracle_rag_data:/data -v ~/lancedb-import:/import alpine \
  sh -c "mkdir -p /data/vector_store/lancedb && cp -r /import/. /data/vector_store/lancedb/"

docker compose restart backend
```
Then regenerate descriptions/examples for each KB from the UI or:
```bash
for kb in $(curl -s https://your-app.duckdns.org/api/kb | python3 -c "import sys,json;print(' '.join(k['name'] for k in json.load(sys.stdin)['knowledge_bases']))"); do
  curl -s -X POST https://your-app.duckdns.org/api/kb/$kb/describe >/dev/null && echo "described $kb"
done
```

---

## Updating the app later

```bash
cd ~/local-rag
git pull
cd deploy/oracle
docker compose up -d --build
```
Your data in the `rag_data` volume is preserved across rebuilds.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Site won't load / cert fails | Ports 80+443 open in **both** the Security List (3a) and OS iptables (3b)? DuckDNS IP correct? |
| `out of host capacity` at VM create | Oracle ARM capacity issue — retry later or try another AD/region. |
| Backend 500 on first KB use | It's downloading the embedding model (~90 MB) on first run; wait and retry. |
| `frontend` container shows Exited | Normal — it's a one-shot builder. Check `docker compose logs frontend`. |
| Chat streams nothing | Confirm your `*_API_KEY` is set in `.env` and `docker compose restart backend`. |

---

## Why Oracle (vs. the alternatives)

Per [free-for.dev](https://free-for.dev), Oracle's Always Free is the only major
provider offering **enough RAM (up to 24 GB) + persistent disk (200 GB) with no
time limit** — AWS/Azure free VMs expire after 12 months and GCP's always-free
`e2-micro` has only 1 GB RAM (too small for the embedding model). Frontend-only or
serverless free tiers (Cloudflare Pages/Workers, Render free) can't keep the
LanceDB/SQLite data persistent the way this app needs.
