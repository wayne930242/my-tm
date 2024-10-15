import os
from typing import Dict
from dotenv import load_dotenv
from my_tm.config.logger import logger


def load_env_config() -> Dict[str, str]:
    """
    Load environment configuration from .env file or system environment.

    Returns:
        A dictionary containing the required environment variables.
    """
    # List of required environment variables
    required_vars = [
        "OPENAI_API_KEY",
        # Add other required variables here
    ]

    # Try to load from .env file
    env_file_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../.env")
    )
    if os.path.exists(env_file_path):
        load_dotenv(env_file_path)
        logger.info(f"Loaded environment from: {env_file_path}")
    else:
        logger.info("No .env file found. Using system environment variables.")

    # Collect environment variables
    env_config = {}
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if value is not None:
            env_config[var] = value
        else:
            missing_vars.append(var)

    # Log status of environment variables
    logger.info("Environment variables status:")
    for var in required_vars:
        status = "Set" if var in env_config else "Missing"
        logger.info(f"{var}: {status}")

    if missing_vars:
        logger.warning(
            f"The following required environment variables are missing: {', '.join(missing_vars)}"
        )
    else:
        logger.info("All required environment variables are set.")

    return env_config


env_config = load_env_config()
