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
# BUILD VALIDATION
# --------------------------------------------------------------------------------
# Optionally runs post-deployment validation once implemented.
# --------------------------------------------------------------------------------
# echo "NOTE: Running build validation..."
# ./validate.sh

# ================================================================================
# END OF SCRIPT
# ================================================================================
