import os
import re
from langchain.text_splitter import MarkdownTextSplitter, RecursiveCharacterTextSplitter

from my_tm.utils.file_utils import read_file
from my_tm.models.chunk_model import FileChunksModel, ProgressEnum, ChunkModel
from my_tm.config.logger import logger
from .state_management_base import StateManagementBase


class TextSplitProcessor(StateManagementBase):
    def __init__(
        self,
        input_directory: str,
        processed_directory: str,
        chunk_size: int = 4000,
        overlap: int = 200,
        state_file: str = "process_state.json",
    ):
        super().__init__(processed_directory, input_directory, state_file)
        self.chunk_size = chunk_size
        self.overlap = overlap

        self.markdown_splitter = MarkdownTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.overlap
        )
        self.default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.overlap
        )

    def process(self) -> None:
        if not self.state.files:
            logger.info("No files found to process.")
            return

        total_split = 0
        total_skipped = 0

        self.state.files.sort(key=self._sort_key)

        for file_state in self.state.files:
            if file_state.progress == ProgressEnum.INIT:
                self._split_file(file_state)
                total_split += 1
            else:
                total_skipped += 1

        logger.info(f"Total files split: {total_split}")
        logger.info(f"Total files skipped: {total_skipped}")

    def _split_file(self, file_state: FileChunksModel) -> None:
        filename = file_state.filename
        full_path = os.path.join(self.input_directory, filename)
        if not os.path.exists(full_path):
            logger.warning(f"File not found: {filename}")
            return

        logger.info(f"Processing file: {filename}")
        try:
            content = read_file(full_path)
            is_markdown = filename.lower().endswith(".md")
            splitter = self.markdown_splitter if is_markdown else self.default_splitter
            chunks = splitter.split_text(content)

            chunk_models = [
                ChunkModel(filename=filename, content=chunk, index=i, total=len(chunks))
                for i, chunk in enumerate(chunks)
            ]

            self.update_file_state(filename, ProgressEnum.SPLITED, chunk_models)
            logger.info(f"Processed and updated state for '{filename}'.")
        except Exception as e:
            logger.error(f"Failed to process file '{filename}': {e}")

    def _sort_key(self, file_state: FileChunksModel) -> tuple:
        """
        Custom sorting function that prioritizes files with leading numbers.
        If the filename starts with a number, sort numerically; otherwise, sort alphabetically.
        """
        filename = file_state.filename
        match = re.match(r"^(\d+)", filename)  # Match leading numbers
        if match:
            # If the filename starts with a number, convert it to an integer for sorting
            return (int(match.group(1)), filename)
        else:
            # If no leading number, sort alphabetically
            return (float("inf"), filename)
