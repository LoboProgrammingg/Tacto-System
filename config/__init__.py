"""
Environment Configuration Module.

Provides automatic environment detection and configuration loading.
Supports: development, staging, production.

Usage:
    from config import get_environment, get_env_file_path
    
    env = get_environment()  # Returns 'development', 'staging', or 'production'
    env_file = get_env_file_path()  # Returns path to correct .env file
"""

import os
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional


class Environment(str, Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    
    @classmethod
    def from_string(cls, value: str) -> "Environment":
        """Convert string to Environment enum."""
        value = value.lower().strip()
        if value in ("dev", "development", "local"):
            return cls.DEVELOPMENT
        if value in ("stg", "staging", "stage"):
            return cls.STAGING
        if value in ("prod", "production", "prd"):
            return cls.PRODUCTION
        return cls.DEVELOPMENT  # Default fallback


def get_git_branch() -> Optional[str]:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def detect_environment_from_branch(branch: Optional[str]) -> Environment:
    """
    Detect environment based on git branch.
    
    Branch mapping:
    - main, master → production
    - staging, release/* → staging
    - dev, develop, feature/*, bugfix/*, hotfix/* → development
    """
    if not branch:
        return Environment.DEVELOPMENT
    
    branch = branch.lower()
    
    # Production branches
    if branch in ("main", "master"):
        return Environment.PRODUCTION
    
    # Staging branches
    if branch == "staging" or branch.startswith("release/"):
        return Environment.STAGING
    
    # Everything else is development
    return Environment.DEVELOPMENT


def get_environment() -> Environment:
    """
    Get current environment.
    
    Priority:
    1. ENVIRONMENT env var (explicit override)
    2. Git branch detection (automatic)
    3. Default to development
    """
    # 1. Check explicit ENVIRONMENT variable
    env_var = os.environ.get("ENVIRONMENT", "").strip()
    if env_var:
        return Environment.from_string(env_var)
    
    # 2. Try git branch detection
    branch = get_git_branch()
    if branch:
        return detect_environment_from_branch(branch)
    
    # 3. Default to development
    return Environment.DEVELOPMENT


def get_project_root() -> Path:
    """Get project root directory."""
    # This file is at config/__init__.py, so go up one level
    return Path(__file__).parent.parent


def get_env_file_path(environment: Optional[Environment] = None) -> Path:
    """
    Get path to environment-specific .env file.
    
    Files are located at: config/environments/.env.{environment}
    """
    if environment is None:
        environment = get_environment()
    
    root = get_project_root()
    env_file = root / "config" / "environments" / f".env.{environment.value}"
    
    # Fallback to root .env if environment-specific doesn't exist
    if not env_file.exists():
        fallback = root / ".env"
        if fallback.exists():
            return fallback
    
    return env_file


def get_env_files() -> list[Path]:
    """
    Get list of .env files to load in order.
    
    Returns files in priority order (later overrides earlier):
    1. .env (base/common settings)
    2. config/environments/.env.{environment} (environment-specific)
    3. .env.local (local overrides, never committed)
    """
    root = get_project_root()
    environment = get_environment()
    
    files = []
    
    # Base .env (optional)
    base_env = root / ".env"
    if base_env.exists():
        files.append(base_env)
    
    # Environment-specific
    env_specific = root / "config" / "environments" / f".env.{environment.value}"
    if env_specific.exists():
        files.append(env_specific)
    
    # Local overrides (never committed)
    local_env = root / ".env.local"
    if local_env.exists():
        files.append(local_env)
    
    return files


# ──────────────────────────────────────────────────────────────────────────────
# Environment Info (for debugging/logging)
# ──────────────────────────────────────────────────────────────────────────────

def get_environment_info() -> dict:
    """Get detailed environment information for debugging."""
    env = get_environment()
    branch = get_git_branch()
    env_files = get_env_files()
    
    return {
        "environment": env.value,
        "git_branch": branch,
        "env_files": [str(f) for f in env_files],
        "is_development": env == Environment.DEVELOPMENT,
        "is_staging": env == Environment.STAGING,
        "is_production": env == Environment.PRODUCTION,
    }
