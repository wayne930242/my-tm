from typing import Dict

from my_tm.config.logger import logger
from my_tm.processors.state_management_base import StateManagementBase
from my_tm.utils.data_utils import load_json
from my_tm.utils.dict_utils import simple_term_replacement
from my_tm.models.chunk_model import FileChunksModel, ProgressEnum


class DictTranslationProcessor(StateManagementBase):
    """
    Class responsible for translating text chunks using a dictionary-based approach.
    It processes files that have been split (state is SPLITED), applies term replacements
    to each chunk, updates the 'diction_translated' field, and updates the file's progress state.
    """

    def __init__(
        self,
        processed_directory: str,
        dict_path: str,
        state_file: str = "process_state.json",
    ):
        """
        Initialize the DictTranslationProcessor with necessary parameters.

        Args:
            processed_directory (str): The directory path where the processed JSON files are saved.
            dict_path (str): The path to the JSON file containing the translation dictionary.
            state_file (str): The filename for storing the unified process state. Default is "process_state.json".
        """
        super().__init__(processed_directory, state_file=state_file)
        self.dict_path = dict_path
        self.translation_dict = self._load_translation_dict()

    def _load_translation_dict(self) -> Dict[str, str]:
        """
        Load the translation dictionary from the specified JSON file.

        Returns:
            Dict[str, str]: The translation dictionary.
        """
        try:
            translation_dict = load_json(self.dict_path)
            logger.info(f"Loaded translation dictionary from '{self.dict_path}'.")
            return translation_dict
        except Exception as e:
            logger.error(
                f"Failed to load translation dictionary from '{self.dict_path}': {e}"
            )
            raise

    def process(self) -> None:
        """
        Main method to process all files in the processed directory.
        Only files that have been split (state is SPLITED) will be processed.
        Applies dictionary-based translations to each chunk and updates the state.
        """
        if not self.state.files:
            logger.info("No files found to process.")
            return

        total_translated = 0
        total_skipped = 0

        for file_state in self.state.files:
            if file_state.progress == ProgressEnum.SPLITED:
                self._translate_file(file_state)
                total_translated += 1
            else:
                total_skipped += 1

        logger.info(f"Total files translated: {total_translated}")
        logger.info(f"Total files skipped: {total_skipped}")

    def _translate_file(self, file_state: FileChunksModel) -> None:
        """
        Translate the chunks of the provided file using the translation dictionary.
        Update the 'diction_translated' field for each chunk and update the file's progress state.

        Args:
            file_state (FileChunksModel): The file state to process.
        """
        filename = file_state.filename
        logger.info(f"Translating file: {filename}")

        try:
            if not file_state.chunks:
                logger.warning(
                    f"No chunks found for file '{filename}'. Skipping translation."
                )
                return

            for chunk in file_state.chunks:
                if chunk.diction_translated is None:
                    chunk.diction_translated = simple_term_replacement(
                        chunk.content, self.translation_dict
                    )
                    logger.debug(f"Translated chunk {chunk.index} of '{filename}'.")
                else:
                    logger.debug(
                        f"Chunk {chunk.index} of '{filename}' already translated."
                    )

            self.update_file_state(
                filename, ProgressEnum.DICTION_TRANSLATED, file_state.chunks
            )
            logger.info(f"Successfully translated and updated '{filename}'.")

        except Exception as e:
            logger.error(f"Failed to translate file '{filename}': {e}")
