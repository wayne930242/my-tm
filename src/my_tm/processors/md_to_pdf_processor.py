from markdown import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
import os
from my_tm.config.logger import logger


class MdToPdfProcessor:
    def __init__(self, processed_directory: str, css_path: str = None) -> None:
        """
        Initialize the MdToPdfProcessor with the directory containing processed Markdown files.

        Args:
            processed_directory (str): The directory path where the processed Markdown files are located.
            css_path (str): Optional path to an external CSS file for styling the PDF.
        """
        self.processed_directory = processed_directory
        self.css_path = css_path or self._get_default_css_path()
        self.font_config = FontConfiguration()
        logger.info("MdToPdfProcessor initialized.")

    def _get_default_css_path(self) -> str:
        """
        Get the default CSS path relative to the script's directory.

        Returns:
            str: The default CSS file path.
        """
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "styles", "default.css")
        )

    def _derive_output_pdf_name(self, filename: str) -> str:
        """
        Derive the output PDF filename from the given markdown filename,
        and place it in the processed_directory.

        Args:
            filename (str): The original markdown filename.

        Returns:
            str: The derived PDF file path.
        """
        if not filename.lower().endswith(".md"):
            logger.warning(
                f"Filename '{filename}' does not end with '.md'. Using original name for PDF."
            )
            pdf_name = f"{filename}.pdf"
        else:
            pdf_name = f"{filename[:-3]}.pdf"

        pdf_path = os.path.join(self.processed_directory, pdf_name)
        logger.debug(f"Derived PDF path for '{filename}': {pdf_path}")
        return pdf_path

    def convert_markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert the Markdown content to HTML.

        Args:
            markdown_content (str): The Markdown content to be converted.

        Returns:
            str: HTML string.
        """
        html_body = markdown(
            markdown_content,
            output_format="html5",
            extensions=["tables", "fenced_code", "codehilite", "toc"],
        )
        logger.debug("Converted Markdown to HTML.")
        return html_body

    def create_pdf(self, html_content: str, output_pdf: str) -> None:
        """
        Create a PDF file from the provided HTML content using WeasyPrint.

        Args:
            html_content (str): HTML string to be converted into PDF.
            output_pdf (str): The filepath where the PDF will be saved.
        """
        logger.info(f"Generating PDF at {output_pdf}.")

        try:
            # Load external CSS
            if self.css_path and os.path.exists(self.css_path):
                css = CSS(filename=self.css_path, font_config=self.font_config)
                logger.debug(f"Loaded external CSS from {self.css_path}.")
            else:
                css = None
                logger.warning(
                    f"CSS path '{self.css_path}' does not exist. Using default styling."
                )

            # Render HTML to PDF
            html = HTML(string=html_content, base_url=self.processed_directory)
            html.write_pdf(
                target=output_pdf,
                stylesheets=[css] if css else None,
                font_config=self.font_config,
                zoom=1,
            )
            logger.debug("PDF generation completed successfully.")
        except Exception as e:
            logger.error(f"Failed to generate PDF for {output_pdf}: {e}")

    def process(self, zoom: float = 1.0, optimize_images: bool = True) -> None:
        """
        Execute the processing steps to generate PDFs from all Markdown files in the processed directory.

        Args:
            zoom (float): The zoom factor in PDF units per CSS units.
            optimize_images (bool): Whether to optimize images in the PDF.
        """
        logger.info(f"Starting PDF generation in directory: {self.processed_directory}")

        # List all .md files in the processed_directory
        md_files = [
            f
            for f in os.listdir(self.processed_directory)
            if os.path.isfile(os.path.join(self.processed_directory, f))
            and f.lower().endswith(".md")
        ]

        if not md_files:
            logger.warning("No Markdown files found in the processed directory.")
            return

        logger.info(f"Found {len(md_files)} Markdown file(s) to process.")

        for filename in md_files:
            md_path = os.path.join(self.processed_directory, filename)
            try:
                with open(md_path, "r", encoding="utf-8") as md_file:
                    markdown_content = md_file.read()
                logger.debug(f"Read Markdown file: {md_path}")
            except Exception as e:
                logger.error(f"Failed to read '{md_path}': {e}")
                continue

            html_content = self.convert_markdown_to_html(markdown_content)
            output_pdf = self._derive_output_pdf_name(filename)
            self.create_pdf(html_content=html_content, output_pdf=output_pdf)
            logger.info(f"PDF created successfully: {output_pdf}")
