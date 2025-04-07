#!/bin/bash
# Script to run the Smee client using environment variables
# This forwards GitHub webhooks from smee.io to the local development server

# Load environment variables from .env file
if [ -f .env ]; then
  echo "Loading environment variables from .env"
  # Only extract and export the specific SMEE variables we need
  export SMEE_URL=$(grep '^SMEE_URL=' .env | cut -d '=' -f 2)
  export SMEE_TARGET=$(grep '^SMEE_TARGET=' .env | cut -d '=' -f 2)
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
