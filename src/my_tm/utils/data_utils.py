from typing import Dict, Any
import os
import json
from my_tm.config.logger import logger


def load_json(file_path: str) -> Dict[str, str]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"Successfully loaded JSON from {file_path}")
            return data
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {str(e)}")
        return {}


def read_json_files_from_folder(folder_path: str) -> Dict[str, Any]:
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"The folder {folder_path} does not exist.")

    result = {}
    json_files = sorted([f for f in os.listdir(folder_path) if f.endswith(".json")])
    for filename in json_files:
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    key = os.path.splitext(filename)[0]
                    result[key] = json.load(file)
            except json.JSONDecodeError:
                logger.error(
                    f"Error decoding JSON from file: {filename}. Skipping this file."
                )
            except Exception as e:
                logger.error(
                    f"Error reading file {filename}: {str(e)}. Skipping this file."
                )

    return result


def save_json(directory: str, filename: str, data: Dict) -> None:
    os.makedirs(directory, exist_ok=True)
    json_filename = f"{os.path.splitext(filename)[0]}.json"
    file_path = os.path.join(directory, json_filename)
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Could not write to file {file_path}: {e}")
