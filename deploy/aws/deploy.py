"""
One-command AEGIS deploy to AWS EC2 (free-tier t3.micro).

Creates: key pair, security group (80 + 22), EC2 instance with Docker,
uploads the project, writes the production .env, starts the app on port 80.
Idempotent-ish: safe to re-run after a failure; reuses existing resources
by name where possible.

Needs in the environment (or .env): AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY.

Usage:
  python deploy/aws/deploy.py                 # full deploy
  python deploy/aws/deploy.py --redeploy      # re-upload code to existing instance
  python deploy/aws/deploy.py --terminate     # tear everything down
"""
import argparse
import io
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

REGION = os.getenv("AWS_REGION", "ap-south-1")
NAME = "aegis-ezor"
KEY_FILE = Path(__file__).resolve().parent / f"{NAME}-key.pem"
INSTANCE_TYPE = "t3.micro"

# The deployed app's .env — same key as local; DEMO mode if it's blank.
PROD_ENV = """\
ANTHROPIC_API_KEY={anthropic_key}
AEGIS_MODEL={model}
"""

USER_DATA = """#!/bin/bash
dnf install -y docker
systemctl enable --now docker
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose --create-dirs
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
curl -SL https://github.com/docker/buildx/releases/download/v0.19.3/buildx-v0.19.3.linux-amd64 \
  -o /usr/local/lib/docker/cli-plugins/docker-buildx
chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
usermod -aG docker ec2-user
"""

# Local-only or generated content; any dot-prefixed path is skipped too.
EXCLUDE = ("data", "__pycache__", "deploy", "docs")


def clients():
    import boto3
    return boto3.client("ec2", region_name=REGION), boto3.client("ssm", region_name=REGION)


def make_zip() -> Path:
    out = Path(__file__).resolve().parent / "aegis-app.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in ROOT.rglob("*"):
            rel = p.relative_to(ROOT)
            if p.is_dir() or any(
                part.startswith(".") or part in EXCLUDE for part in rel.parts
            ):
                continue
            z.write(p, rel.as_posix())
    print(f"packaged {out.name} ({out.stat().st_size // 1024} KB)")
    return out


def get_instance(ec2):
    r = ec2.describe_instances(Filters=[
        {"Name": "tag:Name", "Values": [NAME]},
        {"Name": "instance-state-name", "Values": ["pending", "running"]},
    ])
    for res in r["Reservations"]:
        for inst in res["Instances"]:
            return inst
    return None


def ensure_infra(ec2, ssm) -> str:
    # Key pair
    if not KEY_FILE.exists():
        try:
            ec2.delete_key_pair(KeyName=NAME)
        except Exception:
            pass
        kp = ec2.create_key_pair(KeyName=NAME)
        KEY_FILE.write_text(kp["KeyMaterial"], encoding="utf-8")
        print(f"key pair -> {KEY_FILE}")

    # Security group
    vpc = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    try:
        sg = ec2.create_security_group(
            GroupName=NAME, Description="AEGIS app", VpcId=vpc)["GroupId"]
        ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[
            {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
        ])
        print(f"security group {sg}")
    except Exception:
        sg = ec2.describe_security_groups(
            Filters=[{"Name": "group-name", "Values": [NAME]}]
        )["SecurityGroups"][0]["GroupId"]

    inst = get_instance(ec2)
    if not inst:
        ami = ssm.get_parameter(
            Name="/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
        )["Parameter"]["Value"]
        inst = ec2.run_instances(
            ImageId=ami, InstanceType=INSTANCE_TYPE, KeyName=NAME,
            SecurityGroupIds=[sg], MinCount=1, MaxCount=1, UserData=USER_DATA,
            TagSpecifications=[{"ResourceType": "instance",
                                "Tags": [{"Key": "Name", "Value": NAME}]}],
        )["Instances"][0]
        print(f"launched {inst['InstanceId']} ({INSTANCE_TYPE})")

    iid = inst["InstanceId"]
    ec2.get_waiter("instance_running").wait(InstanceIds=[iid])
    ip = ec2.describe_instances(InstanceIds=[iid])["Reservations"][0]["Instances"][0][
        "PublicIpAddress"]
    print(f"instance running at {ip}")
    return ip


def ssh(ip: str, cmd: str, check: bool = True):
    return subprocess.run(
        ["ssh", "-i", str(KEY_FILE), "-o", "StrictHostKeyChecking=no",
         "-o", "ConnectTimeout=10", f"ec2-user@{ip}", cmd],
        check=check, capture_output=True, text=True)


def wait_for_ssh(ip: str):
    for i in range(30):
        try:
            ssh(ip, "true")
            return
        except Exception:
            time.sleep(10)
    sys.exit("could not reach instance over SSH")


def upload_and_start(ip: str):
    zip_path = make_zip()
    env_text = PROD_ENV.format(
        anthropic_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("AEGIS_MODEL", "claude-sonnet-4-6"),
    )
    env_local = Path(__file__).resolve().parent / "prod.env"
    env_local.write_text(env_text, encoding="utf-8")

    print("waiting for SSH ...")
    wait_for_ssh(ip)
    # user-data may still be installing docker + plugins on first boot
    for _ in range(30):
        if ssh(ip, "sudo docker compose version && sudo docker buildx version",
               check=False).returncode == 0:
            break
        time.sleep(10)

    subprocess.run(["scp", "-i", str(KEY_FILE), "-o", "StrictHostKeyChecking=no",
                    str(zip_path), str(env_local), f"ec2-user@{ip}:~/"], check=True)
    print("uploaded app + env")

    # sudo on the rm: the ./data volume is created by Docker as root, so a
    # plain rm can't clear it on a redeploy.
    ssh(ip, "sudo dnf install -y unzip >/dev/null 2>&1; "
            "sudo rm -rf ~/aegis && mkdir ~/aegis && "
            "unzip -oq ~/aegis-app.zip -d ~/aegis && "
            "mv ~/prod.env ~/aegis/.env")
    r = ssh(ip, "cd ~/aegis && sudo docker compose -f docker-compose.prod.yml up -d --build",
            check=False)
    print(r.stdout[-2000:] or "", r.stderr[-2000:] or "")
    if r.returncode != 0:
        sys.exit("docker compose failed — see output above")
    print(f"\nDEPLOYED -> http://{ip}")


def terminate(ec2):
    inst = get_instance(ec2)
    if inst:
        ec2.terminate_instances(InstanceIds=[inst["InstanceId"]])
        print(f"terminating {inst['InstanceId']}")
    else:
        print("no running instance found")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--redeploy", action="store_true")
    ap.add_argument("--terminate", action="store_true")
    args = ap.parse_args()

    if not os.getenv("AWS_ACCESS_KEY_ID"):
        sys.exit("Set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in .env first.")

    ec2, ssm = clients()
    if args.terminate:
        terminate(ec2)
        return
    if args.redeploy:
        inst = get_instance(ec2)
        if not inst:
            sys.exit("no running instance — run without --redeploy first")
        upload_and_start(inst["PublicIpAddress"])
        return
    ip = ensure_infra(ec2, ssm)
    upload_and_start(ip)


if __name__ == "__main__":
    main()
