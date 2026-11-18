"""Unit tests for deploy-worker action and bulk secret upload."""

import json
import subprocess
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parent.parent
DEPLOY_SH = ACTION_ROOT / "deploy-worker" / "deploy.sh"


def test_deploy_worker_batches_secrets_with_wrangler_secret_bulk(tmp_path):
    (tmp_path / "wrangler.toml").write_text('name = "test-worker"\n', encoding="utf-8")
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    npx_log = tmp_path / "npx.log"
    bulk_json = tmp_path / "bulk.json"

    mock_npx = mock_bin / "npx"
    mock_npx.write_text(f"""#!/usr/bin/env bash
echo "npx $*" >> "{npx_log}"
if [[ "$*" == *"secret bulk"* ]]; then
    cat > "{bulk_json}"
fi
exit 0
""")
    mock_npx.chmod(0o755)

    env = {
        "PATH": f"{mock_bin}:/usr/bin:/bin",
        "CLOUDFLARE_API_TOKEN": "cf-token-123",
        "WORKER_VARS": "GITHUB_OWNER\nSERVER_FQDN\nMISSING_VAR",
        "GITHUB_OWNER": "bumuellp",
        "SERVER_FQDN": "mc.example.com",
        "WORKER_SECRETS": "SECRET_A\nSECRET_B\nUNSET_SECRET",
        "SECRET_A": "alpha-value",
        "SECRET_B": 'quoted "value"\nline2',
    }

    res = subprocess.run(
        ["bash", str(DEPLOY_SH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert res.returncode == 0, res.stderr

    calls = npx_log.read_text().splitlines()
    assert calls == [
        "npx --yes wrangler deploy --var GITHUB_OWNER:bumuellp --var SERVER_FQDN:mc.example.com",
        "npx --yes wrangler secret bulk",
    ]
    assert json.loads(bulk_json.read_text()) == {
        "SECRET_A": "alpha-value",
        "SECRET_B": 'quoted "value"\nline2',
    }
    assert "::add-mask::alpha-value" in res.stdout
    assert "UNSET_SECRET" in res.stdout


def test_deploy_worker_skips_secret_bulk_when_all_secrets_empty(tmp_path):
    (tmp_path / "wrangler.toml").write_text('name = "test-worker"\n', encoding="utf-8")
    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    npx_log = tmp_path / "npx.log"

    mock_npx = mock_bin / "npx"
    mock_npx.write_text(f"""#!/usr/bin/env bash
echo "npx $*" >> "{npx_log}"
exit 0
""")
    mock_npx.chmod(0o755)

    res = subprocess.run(
        ["bash", str(DEPLOY_SH)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={
            "PATH": f"{mock_bin}:/usr/bin:/bin",
            "CLOUDFLARE_API_TOKEN": "cf-token-123",
            "WORKER_SECRETS": "UNSET_ONLY",
        },
    )
    assert res.returncode == 0, res.stderr
    assert npx_log.read_text().splitlines() == ["npx --yes wrangler deploy"]
