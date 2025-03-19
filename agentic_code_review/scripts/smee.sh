#!/bin/bash
# Script to run the Smee client using environment variables
# This forwards GitHub webhooks from smee.io to the local development server

# Change to the directory where the script is located
cd "$(dirname "$0")/../" || exit 1

# Load environment variables from .env file
if [ -f .env ]; then
  echo "Loading environment variables from .env"
  export $(grep -v '^#' .env | xargs)
else
  echo "Error: .env file not found"
  exit 1
fi

# Check if SMEE_URL and SMEE_TARGET are set
if [ -z "$SMEE_URL" ] || [ -z "$SMEE_TARGET" ]; then
  echo "Error: SMEE_URL or SMEE_TARGET not found in environment variables"
  echo "Please make sure these variables are set in your .env file"
  exit 1
fi

echo "Starting Smee client to forward webhooks from $SMEE_URL to $SMEE_TARGET"

# Run the Smee client
exec smee -u "$SMEE_URL" -t "$SMEE_TARGET"
