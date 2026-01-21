#!/bin/bash
# ===============================================================================
# File: validate.sh
# ===============================================================================

# ------------------------------------------------------------------------------
# Step 1: Print out test web application URL.
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# SELECT WEB BUCKET BY PREFIX
# ------------------------------------------------------------------------------
# Finds the S3 bucket used for hosting the web client by matching a
# known prefix. Exactly one bucket must match.
# ------------------------------------------------------------------------------
PREFIX="cnotes"

read -r -a BUCKETS <<< "$(aws s3api list-buckets \
  --query "Buckets[?starts_with(Name, \`${PREFIX}\`)].Name" \
  --output text)"

# ------------------------------------------------------------------------------
# ENFORCE A SINGLE BUCKET MATCH
# ------------------------------------------------------------------------------
# Avoids deploying to the wrong bucket by requiring exactly one match.
# ------------------------------------------------------------------------------
if [[ "${#BUCKETS[@]}" -eq 0 ]]; then
  echo "ERROR: No S3 bucket found starting with '${PREFIX}'" >&2
  exit 1
elif [[ "${#BUCKETS[@]}" -gt 1 ]]; then
  echo "ERROR: Multiple S3 buckets found starting with '${PREFIX}':" >&2
  for b in "${BUCKETS[@]}"; do
    echo "  - ${b}" >&2
  done
  exit 1
fi

BUCKET_NAME="${BUCKETS[0]}"
echo "NOTE: Bucket name is ${BUCKET_NAME}"

# ------------------------------------------------------------------------------
# DETERMINE BUCKET REGION
# ------------------------------------------------------------------------------
# S3 returns "None" for buckets in us-east-1. Normalize this to the
# canonical region name so we can build a correct bucket URL.
# ------------------------------------------------------------------------------
REGION=$(aws s3api get-bucket-location \
  --bucket "${BUCKET_NAME}" \
  --query "LocationConstraint" \
  --output text)

if [[ "${REGION}" == "None" ]]; then
  REGION="us-east-1"
fi

# ------------------------------------------------------------------------------
# BUILD REGION-AWARE BUCKET URL
# ------------------------------------------------------------------------------
# Used for redirect URIs (callback.html) and other hosted assets.
# ------------------------------------------------------------------------------
BUCKET_URL="https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com"

echo "NOTE: Test application URL - ${BUCKET_URL}/index.html"