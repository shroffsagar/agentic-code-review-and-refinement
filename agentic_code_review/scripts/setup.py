#!/usr/bin/env python
"""
Interactive setup script for the Agentic Code Review and Refinement application.

This script guides users through setting up the application, including:
- Checking prerequisites
- Setting up a GitHub App
- Configuring SMEE for local webhook forwarding
- Setting up LLM provider credentials
- Creating an environment configuration file
"""

import os
import shutil
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import secrets
import string
import requests

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.text import Text
from jinja2 import Template

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
ENV_TEMPLATE_PATH = PROJECT_ROOT / ".env.template"
ENV_PATH = PROJECT_ROOT / ".env"

app = typer.Typer(help="Setup script for Agentic Code Review and Refinement")
console = Console()

def display_banner() -> None:
    """Display welcome banner using Rich"""
    title = Text("Agentic Code Review & Refinement", style="bold cyan")
    subtitle = Text("Interactive Setup Script", style="italic")
    
    console.print(Panel.fit(
        f"{title}\n{subtitle}\n\nThis script will guide you through setting up your local environment "
        f"for the Agentic Code Review and Refinement application.",
        border_style="cyan",
        title="Welcome"
    ))

def get_platform_info() -> str:
    """Get the current platform type"""
    system = platform.system().lower()
    
    if system == "darwin":
        return "macos"
    elif system == "linux":
        # Try to determine Linux distribution
        try:
            with open("/etc/os-release") as f:
                os_release = f.read().lower()
                if "ubuntu" in os_release or "debian" in os_release:
                    return "debian"
                elif "fedora" in os_release or "rhel" in os_release or "centos" in os_release:
                    return "rhel"
        except (FileNotFoundError, IOError):
            pass
        return "linux"
    elif system == "windows":
        return "windows"
    else:
        return "unknown"

def run_command(cmd: List[str], shell: bool = False) -> bool:
    """Run a command and return True if it succeeds, False otherwise."""
    try:
        if shell:
            subprocess.run(cmd, check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def check_python_version() -> bool:
    """Check if Python version is 3.10+"""
    python_version = platform.python_version()
    version_parts = tuple(map(int, python_version.split(".")))
    
    if version_parts < (3, 10):
        console.print(f"[red]❌ Python 3.10+ is required. Found version {python_version}[/red]")
        return False
    
    console.print(f"[green]✓ Python version {python_version} detected[/green]")
    return True

def check_poetry() -> bool:
    """Check if Poetry is installed"""
    if not shutil.which("poetry"):
        console.print("[red]❌ Poetry is not installed[/red]")
        console.print("[yellow]Please install Poetry before continuing:[/yellow]")
        console.print("    macOS: brew install poetry")
        console.print("    Other: https://python-poetry.org/docs/#installation")
        sys.exit(1)
    
    console.print("[green]✓ Poetry is installed[/green]")
    return True

def check_npm() -> bool:
    """Check if npm is installed"""
    if not shutil.which("npm"):
        console.print("[yellow]⚠️ npm is not installed (required for SMEE client)[/yellow]")
        return False
    
    console.print("[green]✓ npm is installed[/green]")
    return True

def check_smee() -> bool:
    """Check if SMEE client is installed"""
    if not shutil.which("smee"):
        console.print("[yellow]⚠️ SMEE client is not installed[/yellow]")
        return False
    
    console.print("[green]✓ SMEE client is installed[/green]")
    return True

def install_prerequisites(platform_type: str) -> None:
    """Install prerequisites based on detected platform"""
    # Check Python 3.10+
    if not check_python_version():
        install_python(platform_type)
    
    # Check Poetry (exit if not installed)
    check_poetry()
    
    # Check and install npm if needed for SMEE
    if not check_npm() and Confirm.ask("Would you like to install Node.js and npm?", default=True):
        install_nodejs(platform_type)
    
    # Check and install SMEE if npm is available
    if check_npm() and not check_smee():
        if Confirm.ask("Would you like to install SMEE client globally?", default=True):
            with console.status("Installing SMEE client globally..."):
                try:
                    subprocess.run(["npm", "install", "--global", "smee-client"], check=True)
                    console.print("[green]✓ SMEE client installed successfully[/green]")
                except subprocess.CalledProcessError:
                    console.print("[red]❌ Failed to install SMEE client. You'll need to install it manually.[/red]")
                    console.print("   Run: npm install --global smee-client")
    
    # Install Python dependencies with Poetry
    with console.status("Verifying Python dependencies with Poetry..."):
        try:
            subprocess.run(["poetry", "install"], cwd=PROJECT_ROOT, check=True)
            console.print("[green]✓ Dependencies verified successfully[/green]")
        except subprocess.CalledProcessError:
            console.print("[red]❌ Failed to verify dependencies with Poetry.[/red]")
            sys.exit(1)

def install_python(platform_type: str) -> None:
    """Provide platform-specific Python installation instructions"""
    instructions = {
        "macos": [
            "Option 1: Using Homebrew (recommended):",
            "  brew install python@3.10",
            "",
            "Option 2: Download from python.org:",
            "  Visit https://www.python.org/downloads/ and download Python 3.10+"
        ],
        "debian": [
            "Using apt (for Ubuntu/Debian):",
            "  sudo apt update",
            "  sudo apt install software-properties-common",
            "  sudo add-apt-repository ppa:deadsnakes/ppa",
            "  sudo apt update",
            "  sudo apt install python3.10 python3.10-venv python3.10-dev"
        ],
        "rhel": [
            "For Fedora:",
            "  sudo dnf install python3.10",
            "",
            "For RHEL/CentOS:",
            "  sudo yum install python3.10"
        ],
        "windows": [
            "Download from python.org:",
            "  Visit https://www.python.org/downloads/ and download Python 3.10+",
            "  Make sure to check 'Add Python to PATH' during installation"
        ]
    }.get(platform_type, ["Visit https://www.python.org/downloads/ and download Python 3.10+"])
    
    console.print(Panel("\n".join(instructions), title="Python 3.10+ Installation", border_style="yellow"))
    
    # Auto-install on supported platforms
    if platform_type == "macos" and shutil.which("brew"):
        if Confirm.ask("Would you like the script to attempt to install Python 3.10+ using Homebrew?", default=True):
            with console.status("Installing Python using Homebrew..."):
                if run_command(["brew", "install", "python@3.10"]):
                    console.print("[green]✓ Python 3.10+ installed successfully[/green]")
                    return
                else:
                    console.print("[red]❌ Failed to install Python using Homebrew[/red]")
    elif platform_type == "debian":
        if Confirm.ask("Would you like the script to attempt to install Python 3.10+ using apt?", default=True):
            with console.status("Installing Python 3.10+ using apt (this may require sudo)..."):
                success = True
                cmds = [
                    "sudo apt update",
                    "sudo apt install -y software-properties-common",
                    "sudo add-apt-repository -y ppa:deadsnakes/ppa",
                    "sudo apt update",
                    "sudo apt install -y python3.10 python3.10-venv python3.10-dev"
                ]
                
                for cmd in cmds:
                    if not run_command(cmd, shell=True):
                        success = False
                        break
                
                if success:
                    console.print("[green]✓ Python 3.10+ installed successfully[/green]")
                    return
                else:
                    console.print("[red]❌ Failed to install Python 3.10+[/red]")
    
    console.print("[yellow]Please install Python 3.10+ manually and then re-run this script.[/yellow]")
    sys.exit(1)

def install_nodejs(platform_type: str) -> None:
    """Install Node.js based on platform"""
    instructions = {
        "macos": [
            "Option 1: Using Homebrew (recommended):",
            "  brew install node",
            "",
            "Option 2: Download from nodejs.org:",
            "  Visit https://nodejs.org/en/download/ and download the macOS installer"
        ],
        "debian": [
            "Using apt (for Ubuntu/Debian):",
            "  curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -",
            "  sudo apt install -y nodejs"
        ],
        "rhel": [
            "For Fedora:",
            "  sudo dnf install nodejs",
            "",
            "For RHEL/CentOS:",
            "  curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -",
            "  sudo yum install -y nodejs"
        ],
        "windows": [
            "Download from nodejs.org:",
            "  Visit https://nodejs.org/en/download/ and download the Windows installer"
        ]
    }.get(platform_type, ["Visit https://nodejs.org/en/download/ for instructions"])
    
    console.print(Panel("\n".join(instructions), title="Node.js Installation", border_style="yellow"))
    
    # Auto-install on supported platforms
    if platform_type == "macos" and shutil.which("brew"):
        if Confirm.ask("Would you like the script to attempt to install Node.js using Homebrew?", default=True):
            with console.status("Installing Node.js using Homebrew..."):
                if run_command(["brew", "install", "node"]):
                    console.print("[green]✓ Node.js installed successfully[/green]")
                    return
                else:
                    console.print("[red]❌ Failed to install Node.js using Homebrew[/red]")
    elif platform_type == "debian":
        if Confirm.ask("Would you like the script to attempt to install Node.js using apt?", default=True):
            with console.status("Installing Node.js using apt (this may require sudo)..."):
                success = True
                cmds = [
                    "curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -",
                    "sudo apt install -y nodejs"
                ]
                
                for cmd in cmds:
                    if not run_command(cmd, shell=True):
                        success = False
                        break
                
                if success:
                    console.print("[green]✓ Node.js installed successfully[/green]")
                    return
                else:
                    console.print("[red]❌ Failed to install Node.js[/red]")
    
    console.print("[yellow]Please install Node.js manually and then re-run this script.[/yellow]")

def setup_github_app() -> Dict[str, str]:
    """Guide user through GitHub App setup"""
    console.print(Panel(
        "To use this application, you need to create a GitHub App that will:\n"
        "1. Receive webhook events from GitHub\n"
        "2. Provide authentication for API access\n"
        "3. Define permissions for repository access\n\n"
        "You'll need to gather these pieces of information:\n"
        "- GitHub App ID\n"
        "- Private Key (a .pem file)\n"
        "- Webhook Secret",
        title="GitHub App Setup",
        border_style="cyan"
    ))

    has_app = Confirm.ask("Have you already created a GitHub App?", default=False)
    
    if not has_app:
        instructions = """
### GitHub App Creation Instructions:

1. Go to: https://github.com/settings/apps/new (for personal account)
   or https://github.com/organizations/YOUR-ORG/settings/apps/new (for an organization)

2. Fill in the required fields:
   - GitHub App name: [Your choice, e.g., "My Code Review App"]
   - Homepage URL: [Any valid URL, can be your GitHub profile]
   - Webhook URL: [Use the SMEE URL we'll generate in the next step]
   - Webhook secret: [Create a secure random string]

3. Set the following Repository Permissions:
   - Contents: Read & write
   - Issues: Read & write
   - Metadata: Read-only
   - Pull requests: Read & write

4. Subscribe to events:
   - Pull request
   - Issue comment
   - Pull request review
   - Pull request review comment

5. Choose where the app can be installed: [All accounts or Only this account]

6. Click "Create GitHub App"

7. After creation:
   - Note your App ID from the app settings page
   - Generate a private key and download the .pem file
"""
        console.print(Markdown(instructions))
        
        if not Confirm.ask("Press Y when you have created your GitHub App and have the required information", default=True):
            console.print("[yellow]Setup cancelled. You can re-run this script when you're ready.[/yellow]")
            sys.exit(0)
    
    # Generate a secure webhook secret if needed
    offer_generate_secret = not has_app or Confirm.ask("Would you like to generate a secure webhook secret?", default=False)
    webhook_secret = ""
    
    if offer_generate_secret:
        alphabet = string.ascii_letters + string.digits
        webhook_secret = ''.join(secrets.choice(alphabet) for _ in range(40))
        console.print(f"[green]Generated secure webhook secret: {webhook_secret}[/green]")
        console.print("[yellow]Make sure to update this in your GitHub App settings.[/yellow]")
        
        if not Confirm.ask("Have you updated the webhook secret in your GitHub App settings?", default=True):
            console.print("[yellow]Please update your webhook secret before continuing.[/yellow]")
    
    # Collect GitHub App details
    app_id = IntPrompt.ask("Enter your GitHub App ID")
    
    private_key_path = Prompt.ask("Enter the path to your private key (.pem file)")
    private_key_path = os.path.expanduser(private_key_path)
    
    # Validate and read private key
    try:
        with open(private_key_path, 'r') as f:
            private_key = f.read()
            # Basic validation that it looks like a private key
            if "-----BEGIN RSA PRIVATE KEY-----" not in private_key and "-----BEGIN PRIVATE KEY-----" not in private_key:
                console.print("[red]❌ File does not appear to be a valid private key.[/red]")
                sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Failed to read private key: {e}[/red]")
        sys.exit(1)
    
    # Only ask for webhook secret if we didn't generate one
    if not webhook_secret:
        webhook_secret = Prompt.ask("Enter your GitHub App Webhook Secret")
    
    return {
        "app_id": str(app_id),
        "private_key": private_key,
        "webhook_secret": webhook_secret
    }

def setup_smee() -> Dict[str, str]:
    """Set up SMEE for webhook forwarding"""
    console.print(Panel(
        "SMEE.io is a webhook payload delivery service that will forward "
        "GitHub webhooks to your local development environment.",
        title="SMEE Webhook Forwarding Setup",
        border_style="cyan"
    ))
    
    use_existing = Confirm.ask("Do you already have a SMEE URL?", default=False)
    
    if use_existing:
        smee_url = Prompt.ask(
            "Enter your existing SMEE URL",
            default="https://smee.io/",
            show_default=True
        )
        
        # Validate URL format
        if not smee_url.startswith("https://smee.io/"):
            console.print("[red]❌ Invalid SMEE URL. It should start with https://smee.io/[/red]")
            smee_url = Prompt.ask(
                "Enter a valid SMEE URL",
                default="https://smee.io/",
                show_default=True
            )
    else:
        with console.status("Generating a new SMEE URL..."):
            try:
                response = requests.get("https://smee.io/new")
                smee_url = response.url
                console.print(f"[green]✓ Generated new SMEE URL: {smee_url}[/green]")
                
                console.print("[yellow]⚠️ IMPORTANT: Go to your GitHub App settings and update the Webhook URL "
                             f"to {smee_url}[/yellow]")
                
                if not Confirm.ask("Have you updated the Webhook URL in your GitHub App settings?", default=True):
                    console.print("[yellow]Please update your GitHub App webhook URL before continuing.[/yellow]")
                    console.print(f"[yellow]SMEE URL: {smee_url}[/yellow]")
                    sys.exit(0)
            except Exception as e:
                console.print(f"[red]❌ Failed to generate SMEE URL: {e}[/red]")
                smee_url = Prompt.ask(
                    "Please enter a SMEE URL manually",
                    default="https://smee.io/",
                    show_default=True
                )
    
    # Get local target URL
    target_url = Prompt.ask(
        "Enter your local target URL",
        default="http://localhost:3000/api/webhook",
        show_default=True
    )
    
    return {
        "smee_url": smee_url,
        "target_url": target_url
    }

def setup_llm() -> Dict[str, str]:
    """Set up LLM provider credentials"""
    console.print(Panel(
        "This application uses an LLM (Large Language Model) for code review and refinement.\n"
        "Currently, OpenAI is the supported provider.",
        title="LLM Provider Setup",
        border_style="cyan"
    ))
    
    api_key = Prompt.ask("Enter your OpenAI API Key", password=True)
    
    # Default model suggestions
    model_choices = ["o3-mini", "gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
    model = Prompt.ask(
        "Select the OpenAI model to use",
        choices=model_choices,
        default="o3-mini"
    )
    
    return {
        "api_key": api_key,
        "model": model,
        "provider": "openai"
    }

def create_env_file(github_app: Dict[str, str], smee: Dict[str, str], llm: Dict[str, str]) -> None:
    """Create .env file from collected information using templating"""
    console.print("Creating Environment Configuration...")
    
    # Load template
    if not ENV_TEMPLATE_PATH.exists():
        console.print(f"[red]❌ Template file not found: {ENV_TEMPLATE_PATH}[/red]")
        sys.exit(1)
    
    with open(ENV_TEMPLATE_PATH, 'r') as f:
        template_content = f.read()
    
    # Use Jinja2 templating for better maintainability
    template = Template(template_content)
    env_content = template.render(
        github_app_id=github_app["app_id"],
        github_private_key=github_app["private_key"].strip(),
        github_webhook_secret=github_app["webhook_secret"],
        llm_api_key=llm["api_key"],
        llm_provider=llm["provider"],
        llm_model=llm["model"],
        smee_url=smee["smee_url"],
        smee_target=smee["target_url"]
    )
    
    # Write to .env file
    with open(ENV_PATH, 'w') as f:
        f.write(env_content)
    
    console.print(f"[green]✓ Environment configuration created: {ENV_PATH}[/green]")

def show_startup_instructions(smee: Dict[str, str]) -> None:
    """Show instructions for starting the application"""
    instructions = """
## Startup Instructions

Your configuration is complete! To start using the application:

1. Start the SMEE client (in one terminal):
   ```
   poetry run sh agentic_code_review/scripts/smee.sh
   ```

2. Start the application (in another terminal):
   ```
   poetry run python -m agentic_code_review.github_app
   ```

3. Create a pull request in your repository and add the label "agentic-review" to trigger a review.
   Later, add the label "agentic-refine" to apply suggested changes.

4. To stop the application, press Ctrl+C in both terminals.
"""
    console.print(Markdown(instructions))

@app.command()
def main() -> None:
    """Run the interactive setup process"""
    display_banner()
    
    console.print("\n[bold cyan]Checking System Requirements[/bold cyan]")
    platform_type = get_platform_info()
    console.print(f"Detected platform: [bold]{platform_type}[/bold]")
    
    install_prerequisites(platform_type)
    
    # Setup GitHub App
    console.print("\n[bold cyan]GitHub App Setup[/bold cyan]")
    github_app = setup_github_app()
    
    # Setup SMEE
    console.print("\n[bold cyan]SMEE Webhook Forwarding Setup[/bold cyan]")
    smee = setup_smee()
    
    # Setup LLM
    console.print("\n[bold cyan]LLM Provider Setup[/bold cyan]")
    llm = setup_llm()
    
    # Create .env file
    console.print("\n[bold cyan]Configuration[/bold cyan]")
    create_env_file(github_app, smee, llm)
    
    # Show startup instructions
    console.print("\n[bold cyan]Setup Complete![/bold cyan]")
    show_startup_instructions(smee)

if __name__ == "__main__":
    app() 