# ================================================================================
# File: apply.sh
# ================================================================================

export AWS_DEFAULT_REGION="us-east-1"
set -euo pipefail

# --------------------------------------------------------------------------------
# ENVIRONMENT PRE-CHECK
# --------------------------------------------------------------------------------
# Ensures that required tools, variables, and credentials exist before
# proceeding with resource deployment.
# --------------------------------------------------------------------------------
echo "NOTE: Running environment validation..."
./check_env.sh
if [ $? -ne 0 ]; then
  echo "ERROR: Environment validation failed. Exiting."
  exit 1
fi

# --------------------------------------------------------------------------------
# BUILD LAMBDAS AND API GATEWAY
# --------------------------------------------------------------------------------
# Deploys the Lambda functions and API Gateway endpoints via Terraform.
# --------------------------------------------------------------------------------
echo "NOTE: Building Lambdas and API gateway..."

cd 01-lambdas || { echo "ERROR: 01-lambdas directory missing."; exit 1; }

terraform init
terraform apply -auto-approve

cd .. || exit

# --------------------------------------------------------------------------------
# BUILD SIMPLE WEB APPLICATION
# --------------------------------------------------------------------------------
# Creates a static web client that communicates with the deployed API
# Gateway. Substitutes the API URL into the HTML template.
# --------------------------------------------------------------------------------
API_ID=$(aws apigatewayv2 get-apis \
  --query "Items[?Name=='notes-api'].ApiId" \
  --output text)

if [[ -z "${API_ID}" || "${API_ID}" == "None" ]]; then
  echo "ERROR: No API found with name 'notes-api'"
  exit 1
fi

URL=$(aws apigatewayv2 get-api \
  --api-id "${API_ID}" \
  --query "ApiEndpoint" \
  --output text)

export API_BASE="${URL}"
echo "NOTE: API Gateway URL - ${API_BASE}"

echo "NOTE: Building Simple Web Application..."

cd 02-webapp || { echo "ERROR: 02-webapp directory missing."; exit 1; }

envsubst '${API_BASE}' < index.html.tmpl > index.html || {
  echo "ERROR: Failed to generate index.html file. Exiting."
  exit 1
}

terraform init
terraform apply -auto-approve

cd .. || exit

# --------------------------------------------------------------------------------
# BUILD COGNITO BASED AUTHENTICATION
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

echo "NOTE: Building Cognito Configuration"

cd 03-cognito || { echo "ERROR: 03-cognito directory missing."; exit 1; }

terraform init
terraform apply -auto-approve \
  -var="spa_origin=${BUCKET_URL}"

echo "NOTE: Reading Cognito outputs..."

COGNITO_DOMAIN_PREFIX=$(terraform output -raw cognito_domain)
CLIENT_ID=$(terraform output -raw app_client_id)

if [[ -z "${COGNITO_DOMAIN_PREFIX}" || -z "${CLIENT_ID}" ]]; then
  echo "ERROR: Failed to read Cognito outputs"
  exit 1
fi

if [[ -z "${AWS_REGION}" ]]; then
  echo "ERROR: AWS_REGION is not set"
  exit 1
fi

COGNITO_DOMAIN="${COGNITO_DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com"

echo "NOTE: Writing config.json..."

cat > /tmp/config.json <<EOF
{
  "cognitoDomain": "${COGNITO_DOMAIN}",
  "clientId": "${CLIENT_ID}",
  "redirectUri": "${BUCKET_URL}/callback.html",
  "apiBaseUrl": "${API_BASE}"
}
EOF

echo "NOTE: Uploading config.json to S3..."

aws s3 cp /tmp/config.json "s3://${BUCKET_NAME}/config.json" \
  --content-type "application/json" \
  --cache-control "no-store, max-age=0"

cd .. || exit

# --------------------------------------------------------------------------------
# BUILD VALIDATION
# --------------------------------------------------------------------------------
# Optionally runs post-deployment validation once implemented.
# --------------------------------------------------------------------------------
# echo "NOTE: Running build validation..."
# ./validate.sh

# ================================================================================
# END OF SCRIPT
# ================================================================================
