import os
import json
import tempfile
from typing import List, Optional
from pydantic import ValidationError
from my_tm.utils.data_utils import load_json, save_json
from my_tm.models.chunk_model import (
    ProcessStateModel,
    FileChunksModel,
    ProgressEnum,
    ChunkModel,
)
from my_tm.config.logger import logger


class StateManagementBase:
    def __init__(
        self,
        processed_directory: str,
        input_directory: Optional[str] = None,
        state_file: str = "process_state.json",
    ):
        self.processed_directory = processed_directory
        self.input_directory = input_directory
        self.state_file_path = os.path.join(self.processed_directory, state_file)
        
        # Ensure the processed_directory exists
        if not os.path.exists(self.processed_directory):
            try:
                os.makedirs(self.processed_directory, exist_ok=True)
                logger.info(f"Created processed directory: {self.processed_directory}")
            except Exception as e:
                logger.error(f"Failed to create processed directory {self.processed_directory}: {e}")
                raise
        
        self._cleanup_temp_files()
        self._state = self._load_or_initialize_state()

    def _cleanup_temp_files(self) -> None:
        """
        Remove any leftover temporary state files from previous runs.
        """
        temp_suffix = ".tmp"
        state_basename = os.path.basename(self.state_file_path)
        try:
            for filename in os.listdir(self.processed_directory):
                if filename.startswith(state_basename) and filename.endswith(temp_suffix):
                    temp_file_path = os.path.join(self.processed_directory, filename)
                    try:
                        os.remove(temp_file_path)
                        logger.info(f"Removed leftover temp file: {temp_file_path}")
                    except Exception as e:
                        logger.error(f"Failed to remove temp file {temp_file_path}: {e}")
        except FileNotFoundError:
            logger.warning(f"Processed directory {self.processed_directory} does not exist when attempting to clean up temp files.")
        except Exception as e:
            logger.error(f"Error during cleanup of temp files: {e}")

    def _load_or_initialize_state(self) -> ProcessStateModel:
        if os.path.exists(self.state_file_path):
            try:
                data = load_json(self.state_file_path)
                state = ProcessStateModel(**data)
                logger.info("Loaded existing process state.")
                return state
            except (ValidationError, IOError) as e:
                logger.error(f"Error loading state file: {e}. Initializing new state.")

        if self.input_directory:
            logger.info("Initializing new state with files from input directory.")
            all_files = self._get_all_files()
            new_files = [
                FileChunksModel(filename=f, chunks=[], progress=ProgressEnum.INIT)
                for f in all_files
            ]
            new_state = ProcessStateModel(files=new_files)
        else:
            logger.info("Initializing new empty state.")
            new_state = ProcessStateModel(files=[])

        self._save_state(new_state)
        return new_state

    def _save_state(self, state: ProcessStateModel) -> None:
        temp_file = None
        try:
            # Create a temporary file in the same directory
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.processed_directory,
                prefix=os.path.basename(self.state_file_path) + ".",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                json_data = state.model_dump()
                json_content = json.dumps(json_data, ensure_ascii=False, indent=4)
                temp_file.write(json_content)
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_file_path = temp_file.name

            # Atomically replace the original state file with the temporary file
            os.replace(temp_file_path, self.state_file_path)
            logger.info("Process state saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save process state: {e}")
            # Attempt to remove the temporary file if it exists
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                    logger.info(f"Temporary state file removed: {temp_file.name}")
                except Exception as remove_error:
                    logger.error(
                        f"Failed to remove temporary file {temp_file.name}: {remove_error}"
                    )
        finally:
            # Ensure temp file is removed in case of any remaining issues
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.remove(temp_file.name)
                except:
                    pass  # Already handled in the except block

    def _get_all_files(self) -> List[str]:
        if not self.input_directory:
            return []
        return [
            f
            for f in os.listdir(self.input_directory)
            if os.path.isfile(os.path.join(self.input_directory, f))
        ]

    @property
    def state(self) -> ProcessStateModel:
        return self._state

    @state.setter
    def state(self, new_state: ProcessStateModel) -> None:
        self._state = new_state
        self._save_state(new_state)

    def update_file_state(
        self, filename: str, new_progress: ProgressEnum, chunks: List[ChunkModel] = None
    ) -> None:
        for file_state in self.state.files:
            if file_state.filename == filename:
                file_state.progress = new_progress
                if chunks is not None:
                    file_state.chunks = chunks
                break
        self._save_state(self.state)
