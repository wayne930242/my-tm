from typing import List, Tuple, Optional, Dict
import os
from my_tm.config.logger import logger
from my_tm.processors.state_management_base import StateManagementBase


class OutputMdProcessor(StateManagementBase):
    def __init__(
        self,
        processed_directory: str,
        state_file: str = "process_state.json",
    ) -> None:
        """
        Initialize the OutputMdProcessor with the processed directory and state file.

        Args:
            processed_directory (str): The directory path where the processed Markdown files will be saved.
            state_file (str): The filename for storing the unified process state. Default is "process_state.json".
        """
        super().__init__(processed_directory, state_file)
        # Dictionary to hold translated content per filename
        self.translated_content_per_file: Dict[str, List[Tuple[str, str]]] = {}
        logger.info("OutputMdProcessor initialized.")

    def _derive_output_md_name(
        self, filename: str, bilingual_mode: str = "none"
    ) -> str:
        """
        Derive the output Markdown filename from the given filename,
        and place it in the processed_directory.

        Args:
            filename (str): The original filename.

        Returns:
            str: The derived Markdown file path.
        """
        filenameRemoveExtension = os.path.splitext(filename)[0]
        md_name = f"{filenameRemoveExtension}{'' if bilingual_mode == 'none' else f'_{bilingual_mode}'}.md"

        md_path = os.path.join(self.processed_directory, md_name)
        logger.debug(f"Derived Markdown path for '{filename}': {md_path}")
        return md_path

    def read_translated_content_from_state(self) -> None:
        """
        Extract all original and translated content from each file and its chunks
        within the process state, organizing them per filename.
        """
        logger.info("Extracting original and translated content from process state.")
        for file_data in self.state.files:
            filename = file_data.filename
            if filename not in self.translated_content_per_file:
                self.translated_content_per_file[filename] = []
            for chunk in file_data.chunks:
                original = chunk.content
                translated = chunk.improve_translated
                if translated:
                    self.translated_content_per_file[filename].append(
                        (original, translated)
                    )
                    logger.debug(
                        f"Extracted original and translation from chunk {chunk.index} of '{filename}'."
                    )

    def convert_translated_content_to_markdown(
        self, translated_content: List[Tuple[str, str]], bilingual_mode: str
    ) -> str:
        """
        Convert the aggregated translated Markdown content to a single Markdown string with optional bilingual formatting.

        Args:
            translated_content (List[Tuple[str, str]]): List of tuples containing original and translated text.
            bilingual_mode (str): The mode for bilingual output ('none', 'side-by-side', or 'alternate-pages').

        Returns:
            str: Combined Markdown string.
        """
        if bilingual_mode == "none":
            combined_markdown = "\n\n".join([t for _, t in translated_content])
        elif bilingual_mode == "alternate-pages":
            combined_markdown = self._create_alternate_pages_markdown(
                translated_content
            )
        else:
            raise ValueError(f"Invalid bilingual mode: {bilingual_mode}")

        logger.debug(
            f"Converted aggregated translated content to Markdown with {bilingual_mode} mode."
        )
        return combined_markdown

    def _create_alternate_pages_markdown(
        self, translated_content: List[Tuple[str, str]]
    ) -> str:
        """Create alternate pages Markdown for bilingual content."""
        markdown_content = ""
        for original, translated in translated_content:
            markdown_content += (
                f"{original}\n\n" f"---\n\n" f"{translated}\n\n" f"---\n\n"
            )
        return markdown_content

    def create_md_file(self, markdown_content: str, output_md: str) -> None:
        """
        Write the generated Markdown content to a file.

        Args:
            markdown_content (str): The Markdown string to be written to the file.
            output_md (str): The filepath where the Markdown file will be saved.
        """
        logger.info(f"Generating Markdown file at: {output_md}")
        try:
            with open(output_md, "w", encoding="utf-8") as md_file:
                md_file.write(markdown_content)
            logger.debug("Markdown file generated successfully.")
        except Exception as e:
            logger.error(f"Failed to generate Markdown file: {e}")

    def process(self, bilingual_mode: str = "none") -> None:
        """
        Execute the processing steps to generate Markdown files from the process state.

        Args:
            bilingual_mode (str): The mode for bilingual output ('none', 'side-by-side', or 'alternate-pages').
        """
        self.read_translated_content_from_state()
        if not self.translated_content_per_file:
            logger.warning("No translated content found in the process state.")
            return

        for filename, translated_content in self.translated_content_per_file.items():
            if not translated_content:
                logger.warning(
                    f"No translated content for '{filename}'. Skipping Markdown generation."
                )
                continue

            markdown_content: str = self.convert_translated_content_to_markdown(
                translated_content, bilingual_mode
            )
            output_md = self._derive_output_md_name(filename, bilingual_mode)
            self.create_md_file(markdown_content, output_md)
            logger.info(f"Markdown file created successfully: {output_md}")
