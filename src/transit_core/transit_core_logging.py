import json
import logging
import logging.config
import os
import sys
from pathlib import Path


def setup_logging(path: str = "logs/app.log"):
    # 1. Ground all paths in the project root
    project_root = Path(__file__).parent.parent.parent
    log_config_path = project_root / "logging.json"

    with open(log_config_path, "r") as f:
        logging_config = json.load(f)

    # 2. Ensure the log file path is an absolute string
    log_file_path = project_root / (path or "logs/app.log")
    log_dir = log_file_path.parent
    os.makedirs(log_dir, exist_ok=True)

    # CAST TO STRING: logging handlers don't always like Path objects
    logging_config["handlers"]["file_json"]["filename"] = str(log_file_path)

    # 3. FORCE STDERR: Explicitly override the stream with the sys.stderr object
    # This prevents the 'Unexpected non-whitespace character' error in Claude
    if "handlers" in logging_config and "console" in logging_config["handlers"]:
        logging_config["handlers"]["console"]["stream"] = sys.stderr

    # 4. Apply configuration
    logging.config.dictConfig(logging_config)

    logger = logging.getLogger(__name__)
    # Note: This will now go safely to stderr (and show up in Claude logs)
    logger.info("Logging configured. Standard output reserved for MCP protocol.")
