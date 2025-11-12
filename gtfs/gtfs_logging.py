import logging
import logging.config
import json
import os
import config

def setup_logging():
    with open('logging.json', 'r') as f:
        logging_config = json.load(f)

    log_file_path = config.LOG_FILE_PATH

    log_dir = os.path.dirname(log_file_path)
    if log_dir:
        os.makedirs(log_dir, exist_ok = True)

    logging_config["handlers"]["file_json"]["filename"] = log_file_path

    logging.config.dictConfig(logging_config)

    logger = logging.getLogger(__name__)
    logger.info("Logging has been configured.")