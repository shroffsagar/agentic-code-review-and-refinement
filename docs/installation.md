# Installation Guide

This guide provides detailed instructions for installing and configuring the Agentic Code Review & Refinement application on your local environment.

## Prerequisites

- **Python 3.10+**: Required to run the application
- **Poetry**: Used for dependency management
- **Node.js**: Required for the SMEE client
- **GitHub Account**: Required to create a GitHub App

> **Note:** The interactive setup script can help you install Python, Poetry, and Node.js if they're not already present on your system. You'll be prompted during setup with options to install these prerequisites.

## Setup Process

The easiest way to set up the application is using our interactive setup script:

```bash
python agentic_code_review/scripts/setup.py
```

The script will:
1. Check for prerequisite software and help you install what's missing
2. Guide you through the entire setup process
3. Create all necessary configuration files

### 1. Creating a GitHub App

To use this application, you need to create a GitHub App that will send webhook events to your local environment.

1. Go to GitHub settings:
   - For a personal account: [https://github.com/settings/apps/new](https://github.com/settings/apps/new)
   - For an organization: `https://github.com/organizations/YOUR-ORG/settings/apps/new`

2. Fill in the required fields:
   - **GitHub App name**: Choose a descriptive name (e.g., "My Code Review Bot")
   - **Description**: Brief description of what the app does
   - **Homepage URL**: Any valid URL (can be your GitHub profile)
   - **Callback URL**: Leave blank
   - **Webhook URL**: Use a SMEE URL (see next section)
   - **Webhook secret**: Create a random string (store this safely)

3. Permissions:
   
   **Repository permissions:**
   - **Contents**: Read & write (to commit changes)
   - **Issues**: Read & write (to post comments)
   - **Metadata**: Read-only
   - **Pull requests**: Read & write (to review PRs and post comments)

4. Subscribe to events:
   - Pull request
   - Issue comment
   - Pull request review
   - Pull request review comment

5. Choose where the app can be installed:
   - "Only on this account" (for personal use)
   - "Any account" (if you want to allow others to install it)

6. Click "Create GitHub App"

7. After creation:
   - Note your **App ID** from the app settings page
   - Click "Generate a private key" and download the .pem file
   - Store this key securely, as you cannot download it again

### 2. Setting Up SMEE

SMEE.io is a relay service that forwards GitHub webhooks to your local environment.

1. Visit [https://smee.io/new](https://smee.io/new) to create a new SMEE channel
2. Copy the URL (looks like `https://smee.io/random-string`)
3. Go back to your GitHub App settings and update the Webhook URL to this SMEE URL
4. Save changes to your GitHub App

> **Note:** The setup script can generate a SMEE URL for you automatically.

### 3. Environment Configuration

Create a `.env` file in the project root with the following information:

```
# GitHub App Configuration
GITHUB_APP_ID=your_github_app_id_here
GITHUB_PRIVATE_KEY=your_github_private_key_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# LLM Configuration
LLM_API_KEY=your_llm_api_key_here
LLM_PROVIDER=openai
LLM_MODEL=o3-mini
LLM_TEMPERATURE=0
LLM_MAX_TOKENS=4000

# SMEE Configuration
SMEE_URL=your_smee_url_here
SMEE_TARGET=http://localhost:3000/api/webhook
```

Notes:
- For `GITHUB_PRIVATE_KEY`, paste the entire contents of the .pem file, including the BEGIN and END lines
- For `LLM_API_KEY`, use your OpenAI API key

> **Note:** The setup script will create this file for you automatically based on your inputs.

### 4. Installing the GitHub App

1. Go to your GitHub App's settings page
2. Click on "Install App" in the sidebar
3. Choose which repositories to install the app on
4. Click "Install"

## Starting the Application

Start the application with two separate commands:

1. In one terminal, start the SMEE client:
   ```bash
   poetry run sh agentic_code_review/scripts/smee.sh
   ```

2. In another terminal, start the application server:
   ```bash
   poetry run python -m agentic_code_review.github_app
   ```

Both processes need to be running for the application to work correctly.

## Troubleshooting

### SMEE Issues

- If webhooks aren't being received, check that:
  - Your SMEE URL is correctly set in the GitHub App settings
  - The SMEE client is running
  - The SMEE_URL and SMEE_TARGET in your .env file are correct

### GitHub App Issues

- Verify that your GitHub App has the correct permissions and is subscribed to the right events
- Check that the app is installed on the repositories you're testing with
- Ensure the private key in your .env file is correctly formatted

### Application Server Issues

- Verify that the server is running on the correct port (default: 3000)
- Check the logs for any error messages
- Ensure all environment variables are correctly set in your .env file 