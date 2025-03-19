# Scripts

This directory contains utility scripts for the Agentic Code Review and Refinement system.

## Webhook Forwarding with Smee

The `smee.sh` script provides a reliable way to forward GitHub webhooks from Smee.io to your local development environment:

```bash
# Make sure the script is executable
chmod +x smee.sh

# Run the script
./smee.sh
```

### Requirements

- Node.js (for the smee-client)
- smee-client installed globally: `npm install --global smee-client`
- A valid `.env` file in the agentic_code_review directory with SMEE_URL and SMEE_TARGET defined
