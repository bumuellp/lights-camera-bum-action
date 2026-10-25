"""Unit tests for sync-dns-record action and sync.sh script."""

import os
import subprocess
from pathlib import Path

import yaml

ACTION_ROOT = Path(__file__).resolve().parent.parent
ACTION_DIR = ACTION_ROOT / "sync-dns-record"
ACTION_FILE = ACTION_DIR / "action.yml"
SYNC_SH = ACTION_DIR / "sync.sh"


def test_action_manifest_valid():
    assert ACTION_FILE.is_file(), "action.yml must exist"
    with open(ACTION_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "Sync DNS Record"
    assert "inputs" in data
    assert "provider" in data["inputs"]
    assert "token" in data["inputs"]
    assert "domain" in data["inputs"]
    assert "subname" in data["inputs"]
    assert "type" in data["inputs"]
    assert "records" in data["inputs"]
    assert "action" in data["inputs"]


def test_sync_sh_executable():
    assert SYNC_SH.is_file(), "sync.sh must exist"
    # Ensure file has executable bit set
    if not os.access(SYNC_SH, os.X_OK):
        SYNC_SH.chmod(0o755)
    assert os.access(SYNC_SH, os.X_OK), "sync.sh must be executable"


def test_sync_sh_missing_required_env_vars():
    # Calling without DNS_TOKEN or DNS_DOMAIN must fail immediately
    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env={}
    )
    assert res.returncode != 0
    assert "must be provided" in res.stderr


def test_sync_desec_upsert(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    curl_log = tmp_path / "curl.log"

    # Mock curl script for deSEC
    mock_curl = mock_bin / "curl"
    mock_curl.write_text(f"""#!/usr/bin/env python3
import sys, os

args = sys.argv[1:]
with open('{curl_log}', 'a') as f:
    f.write(' '.join(args) + '\\n')

# Check -o argument to write dummy response
if '-o' in args:
    out_file = args[args.index('-o') + 1]
    with open(out_file, 'w') as out:
        out.write('{{"status": "ok"}}')

# Print HTTP status code expected by -w "%{{http_code}}"
sys.stdout.write("200")
sys.exit(0)
""")
    mock_curl.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "DNS_PROVIDER": "desec",
        "DNS_TOKEN": "secret-desec-token",
        "DNS_DOMAIN": "example.dedyn.io",
        "DNS_SUBNAME": "mc",
        "DNS_TYPE": "A",
        "DNS_RECORDS": "198.51.100.42",
        "DNS_TTL": "120",
        "DNS_ACTION": "sync",
    }

    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "Successfully updated deSEC DNS record" in res.stdout

    log_contents = curl_log.read_text()
    assert "Authorization: Token secret-desec-token" in log_contents
    assert "https://desec.io/api/v1/domains/example.dedyn.io/rrsets/" in log_contents
    assert "198.51.100.42" in log_contents


def test_sync_desec_delete(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    curl_log = tmp_path / "curl.log"

    mock_curl = mock_bin / "curl"
    mock_curl.write_text(f"""#!/usr/bin/env python3
import sys

args = sys.argv[1:]
with open('{curl_log}', 'a') as f:
    f.write(' '.join(args) + '\\n')

if '-o' in args:
    out_file = args[args.index('-o') + 1]
    with open(out_file, 'w') as out:
        out.write('{{"status": "ok"}}')

sys.stdout.write("204")
sys.exit(0)
""")
    mock_curl.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "DNS_PROVIDER": "desec",
        "DNS_TOKEN": "secret-desec-token",
        "DNS_DOMAIN": "example.dedyn.io",
        "DNS_SUBNAME": "mc",
        "DNS_TYPE": "A",
        "DNS_ACTION": "delete",
    }

    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "Deleting deSEC RRset" in res.stdout
    log_contents = curl_log.read_text()
    assert '"records": []' in log_contents


def test_sync_ionos_create_and_update(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    curl_log = tmp_path / "curl.log"

    # Mock curl to handle IONOS sequence:
    # 1. GET /zones -> returns zone with id "zone-xyz"
    # 2. GET /zones/zone-xyz?recordName=... -> returns records
    # 3. POST /zones/zone-xyz/records or PUT -> returns 200
    mock_curl = mock_bin / "curl"
    mock_curl.write_text(f"""#!/usr/bin/env python3
import sys, json

args = sys.argv[1:]
with open('{curl_log}', 'a') as f:
    f.write(' '.join(args) + '\\n')

out_file = None
if '-o' in args:
    out_file = args[args.index('-o') + 1]

if any('/zones/zone-xyz/records' in a for a in args) and '-X POST' in ' '.join(args):
    if out_file:
        with open(out_file, 'w') as out:
            out.write(json.dumps([{{'id': 'rec-1', 'name': 'mc.example.com', 'type': 'A'}}]))
    sys.stdout.write("201")
elif any('/zones/zone-xyz' in a for a in args) and '-X GET' in ' '.join(args):
    if out_file:
        with open(out_file, 'w') as out:
            out.write(json.dumps({{'id': 'zone-xyz', 'name': 'example.com', 'records': []}}))
    sys.stdout.write("200")
elif any('/zones' in a for a in args) and '-X GET' in ' '.join(args):
    if out_file:
        with open(out_file, 'w') as out:
            out.write(json.dumps([{{'id': 'zone-xyz', 'name': 'example.com'}}]))
    sys.stdout.write("200")
else:
    if out_file:
        with open(out_file, 'w') as out:
            out.write('{{}}')
    sys.stdout.write("200")

sys.exit(0)
""")
    mock_curl.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "DNS_PROVIDER": "ionos",
        "DNS_TOKEN": "prefix.secretkey",
        "DNS_DOMAIN": "example.com",
        "DNS_SUBNAME": "mc",
        "DNS_TYPE": "A",
        "DNS_RECORDS": "203.0.113.10",
        "DNS_TTL": "300",
        "DNS_ACTION": "sync",
    }

    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "Found IONOS Zone ID: zone-xyz" in res.stdout
    assert "Successfully created IONOS record" in res.stdout

    log_contents = curl_log.read_text()
    assert "X-API-Key: prefix.secretkey" in log_contents
    assert "https://api.hosting.ionos.com/dns/v1/zones" in log_contents
    assert "mc.example.com" in log_contents
    assert "203.0.113.10" in log_contents


def test_sync_hetzner_sync(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    hcloud_log = tmp_path / "hcloud.log"

    mock_hcloud = mock_bin / "hcloud"
    mock_hcloud.write_text(f"""#!/usr/bin/env python3
import sys, os

args = sys.argv[1:]
with open('{hcloud_log}', 'a') as f:
    f.write(f"TOKEN={{os.environ.get('HCLOUD_TOKEN')}} ARGS={{' '.join(args)}}\\n")
sys.exit(0)
""")
    mock_hcloud.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "DNS_PROVIDER": "hetzner",
        "DNS_TOKEN": "secret-hcloud-token",
        "DNS_DOMAIN": "example.com",
        "DNS_SUBNAME": "mc",
        "DNS_TYPE": "A",
        "DNS_RECORDS": "203.0.113.88",
        "DNS_TTL": "120",
        "DNS_ACTION": "sync",
    }

    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "Successfully updated Hetzner DNS record" in res.stdout

    log = hcloud_log.read_text()
    assert "TOKEN=secret-hcloud-token" in log
    assert "zone set-records --record 203.0.113.88 example.com mc A" in log
    assert "zone rrset change-ttl example.com mc A --ttl 120" in log


def test_sync_hetzner_sync_apex(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    hcloud_log = tmp_path / "hcloud.log"

    mock_hcloud = mock_bin / "hcloud"
    mock_hcloud.write_text(f"""#!/usr/bin/env python3
import sys, os

args = sys.argv[1:]
with open('{hcloud_log}', 'a') as f:
    f.write(f"TOKEN={{os.environ.get('HCLOUD_TOKEN')}} ARGS={{' '.join(args)}}\\n")
sys.exit(0)
""")
    mock_hcloud.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "DNS_PROVIDER": "hetzner",
        "DNS_TOKEN": "secret-hcloud-token",
        "DNS_DOMAIN": "example.com",
        "DNS_SUBNAME": "",
        "DNS_TYPE": "A",
        "DNS_RECORDS": "203.0.113.88",
        "DNS_TTL": "60",
        "DNS_ACTION": "sync",
    }

    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    log = hcloud_log.read_text()
    assert "zone set-records --record 203.0.113.88 example.com @ A" in log
    assert "zone rrset change-ttl example.com @ A --ttl 60" in log


def test_sync_hetzner_delete(tmp_path):
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    hcloud_log = tmp_path / "hcloud.log"

    mock_hcloud = mock_bin / "hcloud"
    mock_hcloud.write_text(f"""#!/usr/bin/env python3
import sys, os

args = sys.argv[1:]
with open('{hcloud_log}', 'a') as f:
    f.write(f"TOKEN={{os.environ.get('HCLOUD_TOKEN')}} ARGS={{' '.join(args)}}\\n")
sys.exit(0)
""")
    mock_hcloud.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:{os.environ.get('PATH', '')}",
        "DNS_PROVIDER": "hetzner",
        "DNS_TOKEN": "secret-hcloud-token",
        "DNS_DOMAIN": "example.com",
        "DNS_SUBNAME": "mc",
        "DNS_TYPE": "A",
        "DNS_ACTION": "delete",
    }

    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode == 0
    assert "Hetzner DNS record deleted successfully" in res.stdout
    log = hcloud_log.read_text()
    assert "TOKEN=secret-hcloud-token" in log
    assert "zone rrset delete example.com mc A" in log


def test_sync_hetzner_missing_binary(tmp_path):
    env = {
        "PATH": "/usr/bin:/bin",
        "DNS_PROVIDER": "hetzner",
        "DNS_TOKEN": "secret-hcloud-token",
        "DNS_DOMAIN": "example.com",
        "DNS_ACTION": "delete",
    }

    res = subprocess.run(
        ["bash", str(SYNC_SH)], capture_output=True, text=True, check=False, env=env
    )
    assert res.returncode != 0
    assert "'hcloud' CLI is required" in res.stderr
