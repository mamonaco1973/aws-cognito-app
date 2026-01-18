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
