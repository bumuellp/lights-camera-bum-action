#!/usr/bin/env bash
# ==============================================================================
# Initialize OpenTofu S3 remote backend with masked credentials & provider cache
# ==============================================================================
set -euo pipefail

echo "::add-mask::$S3_ACCESS_KEY"
echo "::add-mask::$S3_SECRET_KEY"

export AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY"
{
    echo "AWS_ACCESS_KEY_ID=$S3_ACCESS_KEY"
    echo "AWS_SECRET_ACCESS_KEY=$S3_SECRET_KEY"
} >>"$GITHUB_ENV"

if [ -n "${STATE_PASSPHRASE:-}" ]; then
    echo "::add-mask::$STATE_PASSPHRASE"
    export TF_VAR_state_encryption_passphrase="$STATE_PASSPHRASE"
    echo "TF_VAR_state_encryption_passphrase=$STATE_PASSPHRASE" >>"$GITHUB_ENV"
fi

if [ "${CACHE_PROVIDERS:-true}" = "true" ]; then
    CACHE_DIR="${HOME}/.terraform.d/plugin-cache"
    mkdir -p "$CACHE_DIR"
    export TF_PLUGIN_CACHE_DIR="$CACHE_DIR"
    echo "TF_PLUGIN_CACHE_DIR=$CACHE_DIR" >>"$GITHUB_ENV"
fi

echo "Initializing OpenTofu with remote S3 backend..."
echo "Bucket:   $S3_BUCKET"
echo "Endpoint: $S3_ENDPOINT"
echo "Key:      $S3_KEY"

tofu init \
    -backend-config="bucket=$S3_BUCKET" \
    -backend-config="endpoint=$S3_ENDPOINT" \
    -backend-config="key=$S3_KEY" \
    -backend-config="region=$S3_REGION"
