#!/bin/bash
# ================================================================================
# File: destroy.sh
# ================================================================================
# ================================================================================

# --------------------------------------------------------------------------------
# GLOBAL CONFIGURATION
# --------------------------------------------------------------------------------
# Sets the AWS region and enables strict Bash error handling:
#   -e : Exit on any command error
#   -u : Treat unset variables as errors
#   -o pipefail : Fail entire pipeline if any command fails
# --------------------------------------------------------------------------------
export AWS_DEFAULT_REGION="us-east-1"
set -euo pipefail

# --------------------------------------------------------------------------------
# DESTROY COGNITO CONFIGURATION
# --------------------------------------------------------------------------------

PREFIX="notes"

# ------------------------------------------------------------------
# Find buckets starting with PREFIX
# ------------------------------------------------------------------
read -r -a BUCKETS <<< "$(aws s3api list-buckets \
  --query "Buckets[?starts_with(Name, \`${PREFIX}\`)].Name" \
  --output text)"

# ------------------------------------------------------------------
# Enforce exactly ONE match
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# Get bucket region
# ------------------------------------------------------------------
REGION=$(aws s3api get-bucket-location \
  --bucket "${BUCKET_NAME}" \
  --query "LocationConstraint" \
  --output text)

# AWS returns "None" for us-east-1
if [[ "${REGION}" == "None" ]]; then
  REGION="us-east-1"
fi

# ------------------------------------------------------------------
# Construct S3 HTTPS URL
# ------------------------------------------------------------------
BUCKET_URL="https://${BUCKET_NAME}.s3.${REGION}.amazonaws.com"

echo "NOTE: Destroying Cognito Configuration..."

cd 03-cognito || { echo "ERROR: Directory 03-cognito not found."; exit 1; }
terraform init
terraform destroy -auto-approve \
  -var="spa_origin=${BUCKET_URL}"

cd .. || exit

# --------------------------------------------------------------------------------
# DESTROY WEB APPLICATION
# --------------------------------------------------------------------------------
# Destroys the S3 static web app and supporting Terraform resources
# under the 02-webapp directory.
# --------------------------------------------------------------------------------
echo "NOTE: Destroying Web Application..."

cd 02-webapp || { echo "ERROR: Directory 02-webapp not found."; exit 1; }
terraform init
terraform destroy -auto-approve
cd .. || exit

# --------------------------------------------------------------------------------
# DESTROY LAMBDAS AND API GATEWAY
# --------------------------------------------------------------------------------
# Removes the Lambda functions and associated API Gateway routes
# created during deployment.
# --------------------------------------------------------------------------------
echo "NOTE: Destroying Lambdas and API Gateway..."

cd 01-lambdas || { echo "ERROR: Directory 01-lambdas not found."; exit 1; }
terraform init
terraform destroy -auto-approve
cd .. || exit

echo "NOTE: Infrastructure teardown complete."

# ================================================================================
# END OF SCRIPT
# ================================================================================
