# 16 · AWS deployment — `deploy/aws/deploy.py` + `docker-compose.prod.yml`

One-command deployment of AEGIS to a free-tier EC2 instance. Creates all AWS
resources, uploads the code, and starts the Dockerised app on port 80.

```
python deploy/aws/deploy.py               # full deploy → prints http://<ip>
python deploy/aws/deploy.py --redeploy    # push new code to the same instance
python deploy/aws/deploy.py --terminate   # tear the instance down
```

Requires in `.env`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
(IAM user with AdministratorAccess), optional `AWS_REGION` (default
`ap-south-1`, Mumbai). The deployed app inherits `ANTHROPIC_API_KEY` from the
local `.env` — blank key = DEMO mode; after recharging credit, uncomment the
key locally and run `--redeploy`.

---

## `docker-compose.prod.yml` — line by line

```yaml
services:
  aegis:                       # single service — the whole product
    build: .                   # build from the repo's Dockerfile
    ports:
      - "80:8000"              # public port 80 → uvicorn's 8000 inside
    env_file:
      - .env                   # inject the server-side .env written by deploy.py
    volumes:
      - ./data:/app/data       # SQLite survives container rebuilds
    restart: unless-stopped    # auto-restart on crash or instance reboot
```

Differs from the dev `docker-compose.yml` only in the port mapping (80 vs
8000) and taking config from `env_file` instead of two inline variables.

---

## `deploy.py` — section by section

### Constants (top of file)

```python
REGION = os.getenv("AWS_REGION", "ap-south-1")   # Mumbai default
NAME = "aegis-ezor"                              # tag/name for every AWS resource
KEY_FILE = ...  f"{NAME}-key.pem"                # SSH private key saved locally
INSTANCE_TYPE = "t3.micro"                       # free-tier eligible size
```

```python
PROD_ENV = """\
ANTHROPIC_API_KEY={anthropic_key}    # copied from the local .env at deploy time
AEGIS_MODEL={model}
"""
```
The server's entire configuration. Blank key → the deployed app runs DEMO.

```python
USER_DATA = """#!/bin/bash ..."""
```
Cloud-init script EC2 runs once on first boot: installs Docker, enables the
service, installs the compose plugin, and lets `ec2-user` run Docker.

```python
EXCLUDE = ("data", "__pycache__", "deploy", "docs")
```
Names left out of the upload zip, plus every dot-prefixed path (`.env`,
`.venv`, `.git`, …) — local-only or generated content. The local `.env` is
excluded deliberately; the server gets its own minimal one.

### `clients()`
Builds the two boto3 clients used: `ec2` (all infrastructure) and `ssm`
(only to resolve the latest Amazon Linux 2023 AMI id without hardcoding it).

### `make_zip()`
Walks the repo (`ROOT.rglob`), skips anything whose path contains an
`EXCLUDE` name, and writes `aegis-app.zip` next to the script. Forward-slash
(`as_posix`) paths keep the zip Linux-friendly when built on Windows.

### `get_instance(ec2)`
Looks up an instance tagged `Name=aegis-ezor` in `pending`/`running` state.
Returning `None` means "nothing deployed yet" — this is what makes re-runs
idempotent instead of launching duplicates.

### `ensure_infra(ec2, ssm) -> ip`
Creates, in order, each resource *only if missing*:
1. **Key pair** — created via `create_key_pair`, private key saved to
   `KEY_FILE` (AWS never shows it again, hence saved immediately). A stale
   server-side key with no local file is deleted first so they can't diverge.
2. **Security group** — in the default VPC, opens TCP 80 (public app) and
   TCP 22 (SSH for the deploy itself). If it already exists, `create` raises
   and the `except` block just looks it up instead.
3. **Instance** — latest AL2023 AMI (resolved via the public SSM parameter),
   `t3.micro`, the key pair, the security group, and `USER_DATA`. Then waits
   for the `instance_running` state and returns the public IP.

### `ssh()` / `wait_for_ssh()`
Thin wrappers over the system `ssh` binary (present on Windows 10+ and
Linux/macOS). `StrictHostKeyChecking=no` avoids the interactive fingerprint
prompt on first connect. `wait_for_ssh` polls up to 5 minutes because a
fresh instance takes ~1 minute to accept connections.

### `upload_and_start(ip)`
1. Builds the zip and writes `prod.env` (the rendered `PROD_ENV`).
2. Waits for SSH **and** for `docker` to exist (user-data may still be
   installing it on first boot).
3. `scp`s both files to the instance.
4. Unzips into `~/aegis`, moves `prod.env` → `~/aegis/.env`.
5. `docker compose -f docker-compose.prod.yml up -d --build` — builds the
   image on the instance and starts it detached on port 80.
6. Prints `DEPLOYED -> http://<ip>`.

### `terminate(ec2)`
Finds the tagged instance and terminates it (stops billing). Key pair and
security group are left behind — both are free and reused on the next deploy.

### `main()`
Arg parsing + guardrails: refuses to run without AWS keys in the
environment, then dispatches to terminate / redeploy / full deploy.

---

## Post-deploy operations

| Task | Command |
|---|---|
| Update code on the server | `python deploy/aws/deploy.py --redeploy` |
| Flip DEMO → LIVE after recharge | uncomment key in local `.env`, then `--redeploy` |
| Watch server logs | `ssh -i deploy/aws/aegis-ezor-key.pem ec2-user@<ip> "cd aegis && sudo docker compose -f docker-compose.prod.yml logs -f"` |
| Tear down | `python deploy/aws/deploy.py --terminate` |

Cost: `t3.micro` is inside the AWS free tier (750 h/month for new accounts);
otherwise ≈ $8/month in `ap-south-1`. Port 80 is plain HTTP — fine for a
demo link; put CloudFront or a Caddy container in front if HTTPS is needed.
