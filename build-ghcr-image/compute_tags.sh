#!/usr/bin/env bash
set -euo pipefail

REGISTRY="${1:-ghcr.io}"
REPO_OWNER="${2:?Repository owner is required}"
IMAGE_NAME="${3:?Image name is required}"
SHA="${4:-}"
EXTRA_TAGS="${5:-}"

# Deduplicated tag list
declare -A SEEN_TAGS
TAG_LIST=()

add_tag() {
	local t="$1"
	t="$(echo "$t" | xargs)"
	if [ -n "$t" ] && [ -z "${SEEN_TAGS[$t]:-}" ]; then
		SEEN_TAGS["$t"]=1
		TAG_LIST+=("${REGISTRY}/${REPO_OWNER}/${IMAGE_NAME}:${t}")
	fi
}

# 1. Always include 'latest'
add_tag "latest"

# 2. Include commit SHA if provided
if [ -n "$SHA" ]; then
	add_tag "$SHA"
fi

# 3. Process extra tags and derive SemVer hierarchy
HAS_SEMVER_TAG=false
if [ -n "$EXTRA_TAGS" ]; then
	IFS=', ' read -r -a EXTRA_ARRAY <<<"$EXTRA_TAGS"
	for tag in "${EXTRA_ARRAY[@]}"; do
		tag="$(echo "$tag" | xargs)"
		[ -z "$tag" ] && continue

		# Check if tag is SemVer (e.g. v1.2.3 or 1.2.3)
		if [[ "$tag" =~ ^v?([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
			HAS_SEMVER_TAG=true
			major="${BASH_REMATCH[1]}"
			minor="${BASH_REMATCH[2]}"
			patch="${BASH_REMATCH[3]}"

			prefix=""
			[[ "$tag" =~ ^v ]] && prefix="v"

			# Exact SemVer tag (e.g. v1.2.3)
			add_tag "${prefix}${major}.${minor}.${patch}"
			# Floating minor tag (e.g. v1.2)
			add_tag "${prefix}${major}.${minor}"
			# Floating major tag (e.g. v1)
			add_tag "${prefix}${major}"
		else
			add_tag "$tag"
		fi
	done
fi

# 4. If no explicit SemVer tag was passed (e.g., standard push to main),
# dynamically determine the active major tag from the latest git tag.
if [ "$HAS_SEMVER_TAG" = "false" ]; then
	LATEST_GIT_TAG="$(git describe --tags --abbrev=0 2>/dev/null || true)"
	if [[ "$LATEST_GIT_TAG" =~ ^v?([0-9]+) ]]; then
		MAJOR_TAG="v${BASH_REMATCH[1]}"
	else
		MAJOR_TAG="v1"
	fi
	add_tag "$MAJOR_TAG"
fi

# Output all tags separated by newline
printf '%s\n' "${TAG_LIST[@]}"
