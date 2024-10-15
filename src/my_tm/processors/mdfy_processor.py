import os
import re
from PyPDF2 import PdfReader
from ebooklib import epub
from markdownify import markdownify as md
from my_tm.config.logger import logger

from docx import Document


class MdfyProcessor:
    """
    A processor class to convert PDF, EPUB, or DOCX files to Markdown,
    process the text to remove unwanted line breaks,
    and save them into a specified directory.
    Processes all eligible files within an input directory.
    """

    def __init__(self, input_dir: str, output_dir: str) -> None:
        """
        Initializes the Processor with the input directory and output directory.

        :param input_dir: Path to the directory containing input PDF, EPUB, or DOCX files.
        :param output_dir: Directory where Markdown files will be saved.
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.supported_formats = {"pdf", "epub", "docx"}

        logger.info(
            f"Initialized MdfyProcessor with input_dir='{self.input_dir}' and output_dir='{self.output_dir}'."
        )

    def process(self) -> None:
        """
        Main method to process all eligible files in the input directory
        and convert them to Markdown.
        """
        logger.info("Starting processing of files.")

        if not os.path.isdir(self.input_dir):
            logger.error(f"Input path '{self.input_dir}' is not a directory.")
            raise NotADirectoryError(
                f"Input path '{self.input_dir}' is not a directory."
            )

        # List all files in the input directory
        try:
            files = os.listdir(self.input_dir)
        except Exception as e:
            logger.error(f"Failed to list files in the input directory: {e}")
            raise

        eligible_files = [f for f in files if self._is_supported(f)]
        logger.info(f"Found {len(eligible_files)} supported files to process.")

        if not eligible_files:
            logger.warning(
                "No supported PDF, EPUB, or DOCX files found in the input directory."
            )
            print("No supported PDF, EPUB, or DOCX files found in the input directory.")
            return

        for file_name in eligible_files:
            file_path = os.path.join(self.input_dir, file_name)
            file_ext = self._get_file_extension(file_name)

            logger.info(f"Processing '{file_name}' with extension '{file_ext}'.")

            try:
                if file_ext == "pdf":
                    text = self._process_pdf(file_path)
                elif file_ext == "epub":
                    text = self._process_epub(file_path)
                elif file_ext == "docx":
                    text = self._process_docx(file_path)
                else:
                    # This condition should not be reached due to the earlier filtering
                    logger.warning(f"Skipping unsupported file format: {file_ext}")
                    print(f"Skipping unsupported file format: {file_ext}")
                    continue

                # Process text to remove unwanted line breaks
                cleaned_text = self._clean_text(text)

                # Convert to Markdown
                markdown_content = md(cleaned_text)

                # Define the output file path (single Markdown file per input file)
                file_base_name = os.path.splitext(file_name)[0]
                markdown_filename = f"{file_base_name}.md"
                file_output_path = os.path.join(self.output_dir, markdown_filename)
                os.makedirs(self.output_dir, exist_ok=True)

                # Write to Markdown file
                with open(file_output_path, "w", encoding="utf-8") as f:
                    f.write(f"# {file_base_name}\n\n{markdown_content}")

                logger.info(
                    f"Successfully processed and saved '{file_name}' to '{file_output_path}'."
                )
                print(
                    f"Successfully processed '{file_name}' and saved to '{file_output_path}'.\n"
                )

            except Exception as e:
                logger.error(f"Failed to process '{file_name}': {e}")
                print(f"Failed to process '{file_name}': {e}\n")

        logger.info("Completed processing of all files.")

    def _is_supported(self, file_name: str) -> bool:
        """
        Checks if the file has a supported extension.

        :param file_name: Name of the file.
        :return: True if supported, False otherwise.
        """
        ext = self._get_file_extension(file_name)
        is_supported = ext in self.supported_formats
        return is_supported

    def _get_file_extension(self, file_name: str) -> str:
        """
        Retrieves the file extension of the given file name.

        :param file_name: Name of the file.
        :return: File extension in lowercase without the dot.
        """
        _, ext = os.path.splitext(file_name)
        return ext.lower().strip(".")

    def _process_pdf(self, pdf_path: str) -> str:
        """
        Extracts text from a PDF file using PyPDF2.

        :param pdf_path: Path to the PDF file.
        :return: Extracted text.
        """
        logger.info(f"Extracting text from PDF: '{pdf_path}'.")
        try:
            with open(pdf_path, "rb") as file:
                reader = PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF file '{pdf_path}': {e}")
            raise

    def _process_epub(self, epub_path: str) -> str:
        """
        Extracts content from an EPUB file.

        :param epub_path: Path to the EPUB file.
        :return: Extracted text.
        """
        logger.info(f"Reading EPUB file: '{epub_path}'.")
        book = epub.read_epub(epub_path)
        full_text = ""
        for item in book.get_items():
            if item.get_type() == epub.ITEM_DOCUMENT:
                try:
                    content = item.get_content().decode("utf-8")
                    full_text += content + "\n"
                except Exception as e:
                    logger.warning(
                        f"Failed to decode content from item '{item.get_id()}': {e}"
                    )

        # Convert HTML to plain text
        plain_text = md(full_text)

        return plain_text

    def _process_docx(self, docx_path: str) -> str:
        """
        Extracts text from a DOCX file using python-docx.

        :param docx_path: Path to the DOCX file.
        :return: Extracted text.
        """
        logger.info(f"Extracting text from DOCX: '{docx_path}'.")
        try:
            doc = Document(docx_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return "\n".join(full_text)
        except Exception as e:
            logger.error(f"Error extracting text from DOCX file '{docx_path}': {e}")
            raise

    def _clean_text(self, text: str) -> str:
        """
        Cleans the text by removing unwanted line breaks while preserving line breaks for titles.

        - Retains line breaks after periods (.)
        - Preserves line breaks that are likely to be titles
        - Replaces other line breaks with spaces

        :param text: The raw extracted text.
        :return: Cleaned text.
        """
        logger.info(
            "Starting text cleaning to remove unwanted line breaks while preserving titles."
        )

        # Split the text into lines
        lines = text.split("\n")

        cleaned_lines = []
        abbreviation_pattern = re.compile(
            r"^\w+\.$"
        )  # Pattern to detect single word abbreviations

        for i, line in enumerate(lines):
            stripped_line = line.strip()
            if not stripped_line:
                continue  # Skip empty lines

            # Detect if the line is a single word abbreviation (e.g., "e.g.")
            if abbreviation_pattern.match(stripped_line):
                if cleaned_lines:
                    # Append the abbreviation directly to the previous line without adding a space
                    cleaned_lines[-1] = cleaned_lines[-1].rstrip() + stripped_line + " "
                else:
                    # If there's no previous line, treat it as a regular line
                    cleaned_lines.append(stripped_line + " ")
                continue  # Move to the next line

            # Heuristic to detect if the line is a title
            # Example heuristics:
            # 1. All words start with uppercase letters
            # 2. Line does not end with typical sentence-ending punctuation
            # 3. Line is relatively short (e.g., less than 100 characters)
            # 4. Line contains certain keywords or patterns (optional)

            words = stripped_line.split()
            if len(stripped_line) < 100:
                starts_with_upper = all(word[0].isupper() for word in words if word)
                ends_with_punctuation = stripped_line[-1] in ".!?"
                is_all_caps = stripped_line.isupper()
                # Additional condition: check if line is all caps
                if (starts_with_upper or is_all_caps) and not ends_with_punctuation:
                    # Likely a title, retain the line break
                    cleaned_lines.append(stripped_line + "\n")
                    continue  # Move to the next line

            # If not a title, replace line break with space and ensure sentence starts with uppercase
            if cleaned_lines:
                # Ensure the first character is uppercase
                if not stripped_line[0].isupper():
                    stripped_line = stripped_line[0].upper() + stripped_line[1:]
                cleaned_lines.append(stripped_line + " ")
            else:
                # If it's the first line, ensure it starts with uppercase
                if stripped_line and not stripped_line[0].isupper():
                    stripped_line = stripped_line[0].upper() + stripped_line[1:]
                cleaned_lines.append(stripped_line + " ")

        # Join the cleaned lines
        cleaned_text = "".join(cleaned_lines)

        # Replace multiple spaces with a single space
        cleaned_text = re.sub(r"\s+", " ", cleaned_text)

        # Restore line breaks after periods if they are followed by a space
        # Ensure that abbreviations are not affected by this replacement
        # This regex adds a newline after a period that is followed by a space and a capital letter
        cleaned_text = re.sub(r"\.(?=\s[A-Z])", ".\n", cleaned_text)

        return cleaned_text.strip()
