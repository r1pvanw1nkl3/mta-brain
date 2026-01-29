import json
import logging
import logging.config
import os


def setup_logging(path: str = "logs/app.log"):
    with open("logging.json", "r") as f:
        logging_config = json.load(f)

    if path:
        log_file_path = path
    else:
        log_file_path = "logs/app.log"

    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logging_config["handlers"]["file_json"]["filename"] = log_file_path

    logging.config.dictConfig(logging_config)

    logger = logging.getLogger(__name__)
    logger.info("Logging has been configured.")
