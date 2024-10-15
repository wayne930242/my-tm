import os
import shutil
import math
from typing import List, Tuple
from my_tm.config.logger import logger


def save_file(directory: str, filename: str, content: str) -> None:
    os.makedirs(directory, exist_ok=True)
    logger.debug(f"Saving content for {filename}")

    file_path = os.path.join(directory, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)
        logger.debug(f"Content successfully written to {file_path}")
    except Exception as e:
        logger.error(f"Could not write to file {file_path}: {e}")


def delete_directory(directory: str) -> None:
    if os.path.exists(directory):
        logger.info(f"Deleting directory {directory}")
        shutil.rmtree(directory)
    else:
        logger.info(f"Directory {directory} does not exist")


def read_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
