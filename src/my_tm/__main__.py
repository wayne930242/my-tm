import os
import argparse
from my_tm.processors.mdfy_processor import MdfyProcessor
from my_tm.processors.dict_tranlation_processor import DictTranslationProcessor
from my_tm.processors.output_md_processor import OutputMdProcessor
from my_tm.processors.text_split_processor import TextSplitProcessor
from my_tm.processors.translate_agent_processor import TranslateAgentProcessor
from my_tm.processors.md_to_pdf_processor import MdToPdfProcessor
from my_tm.config.logger import logger


def get_project_root():
    """Return the project root directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def create_parser():
    parser = argparse.ArgumentParser(
        description="Process Markdown files and manage environment."
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Command to execute"
    )

    # Parser for test-load-env command
    subparsers.add_parser("test-load-env", help="Test loading of environment variables")

    # Parser for translate command
    translate_parser = subparsers.add_parser(
        "translate", help="Translate Markdown files"
    )
    translate_parser.add_argument(
        "project_name",
        help="Name of the project directory located within the 'projects' folder",
    )
    translate_parser.add_argument(
        "--chunk-size", type=int, default=4000, help="Size of each chunk"
    )
    translate_parser.add_argument(
        "--overlap", type=int, default=0, help="Overlap between chunks"
    )
    translate_parser.add_argument("--custom-prompt", type=str, default=None, help="Custom prompt for LLM")
    translate_parser.add_argument(
        "--auto-index",
        action="store_true",
        help="Enable automatic book_info indexing and updating [DEPRECATED]",
    )

    # Parser for mdfy command
    mdfy_parser = subparsers.add_parser(
        "mdfy", help="Convert PDF or EPUB files to Markdown"
    )
    mdfy_parser.add_argument(
        "project_name",
        help="Name of the project directory located within the 'projects' folder",
    )

    # Parser result to md command
    result_parser = subparsers.add_parser(
        "result", help="Generate output from translated Markdown files"
    )
    result_parser.add_argument(
        "project_name",
        help="Name of the project directory located within the 'projects' folder",
    )

    # Parser for output command
    output_parser = subparsers.add_parser(
        "output", help="Generate output from translated Markdown files"
    )
    output_parser.add_argument(
        "project_name",
        help="Name of the project directory located within the 'projects' folder",
    )
    output_parser.add_argument(
        "--type",
        type=str,
        choices=["pdf"],
        default="pdf",
        help="Type of output to generate",
    )
    output_parser.add_argument(
        "--bilingual",
        choices=["none", "alternate-pages"],
        default="none",
        help="Bilingual output mode (none or alternate-pages) [USELESS]",
    )

    return parser


def parse_arguments():
    parser = create_parser()
    return parser.parse_args()


def get_project_path(project_root: str, project_name: str) -> str:
    return os.path.join(project_root, "projects", project_name)


def process_result(project_path: str):
    """
    Process the result generation workflow:
    1. Read processed files from the specified directory.
    2. Generate output files from the processed files.
    """
    processed_path = os.path.join(project_path, "processed")
    if not os.path.exists(processed_path):
        logger.error(f"Processed directory '{processed_path}' does not exist.")
        return
    md_processor = OutputMdProcessor(
        processed_directory=processed_path,
    )
    md_processor.process("none")
    md_processor.process("alternate-pages")


def process_translate(
    project_path: str,
    glossary_path: str,
    chunk_size: int,
    overlap: int,
    auto_index: bool,
    custom_prompt: str = None,
):
    """
    Process the translation workflow:
    1. Split Markdown files into chunks.
    2. Apply dictionary-based translation.
    3. Apply LLM-based translation with optional book_info indexing.
    """
    input_path = os.path.join(project_path, "md_files")
    processed_path = os.path.join(project_path, f"processed")

    if not os.path.exists(input_path):
        logger.error(f"Input path '{input_path}' does not exist.")
        return

    files_to_translate = [f for f in os.listdir(input_path) if f.endswith(".md")]

    if not files_to_translate:
        logger.error(
            f"No markdown files found in '{input_path}'. The extension must be '.md'."
        )
        return

    # Split Markdown files into chunks
    split_processor = TextSplitProcessor(
        input_directory=input_path,
        processed_directory=processed_path,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    split_processor.process()

    # Translate chunks using a dictionary
    dict_processor = DictTranslationProcessor(
        processed_directory=processed_path,
        dict_path=glossary_path,
    )
    dict_processor.process()

    # Translate chunks using a language model with auto_index parameter
    llm_processor = TranslateAgentProcessor(
        processed_directory=processed_path,
        glossary_path=glossary_path,
        auto_index=auto_index,  # Pass the auto_index parameter
        custom_prompt=custom_prompt,
    )
    llm_processor.process()

    md_processor = OutputMdProcessor(
        processed_directory=processed_path,
    )
    md_processor.process("none")
    md_processor.process("alternate-pages")


def process_output(project_path: str, output_type: str) -> None:
    """
    Process translated Markdown files and generate the specified output type.

    :param project_path: Path to the project directory.
    :param output_type: Type of output to generate (e.g., 'pdf').
    """
    input_directory = os.path.join(project_path, "processed")
    if not os.path.exists(input_directory):
        logger.error(f"Processed directory '{input_directory}' does not exist.")
        return

    if output_type == "pdf":
        processor = MdToPdfProcessor(
            processed_directory=input_directory,
        )
        processor.process()


def main():
    args = parse_arguments()
    project_root = get_project_root()

    if args.command == "mdfy":
        project_path = get_project_path(project_root, args.project_name)
        input_path = os.path.join(project_path, "origin_files")
        output_path = os.path.join(project_path, "md_files")

        if not os.path.exists(project_path):
            logger.error(f"Project directory '{project_path}' does not exist.")
            return

        process_mdfy = MdfyProcessor(input_path, output_path)
        process_mdfy.process()

    elif args.command == "result":
        project_path = get_project_path(project_root, args.project_name)
        process_result(project_path)

    elif args.command == "translate":
        project_path = get_project_path(project_root, args.project_name)
        glossary_path = os.path.join(project_path, "glossary.json")

        if not os.path.exists(project_path):
            logger.error(f"Project directory '{project_path}' does not exist.")
            return

        if not os.path.exists(glossary_path):
            logger.warning(
                f"Glossary file '{glossary_path}' does not exist. Skipping glossary translation."
            )

        process_translate(
            project_path,
            glossary_path,
            args.chunk_size,
            args.overlap,
            args.auto_index,
            args.custom_prompt,
        )

    elif args.command == "output":
        project_path = get_project_path(project_root, args.project_name)
        output_type = args.type
        bilingual_mode = args.bilingual

        if not os.path.exists(project_path):
            logger.error(f"Project directory '{project_path}' does not exist.")
            return

        process_output(project_path, output_type, bilingual_mode)

    elif args.command == "test-load-env":
        from my_tm.config.env import env_config

        logger.info("Environment variables loaded successfully.")


if __name__ == "__main__":
    main()
