# p_v_monster

## Installation

```bash
# Install dependencies
poetry install
```

### WeasyPrint

```bash
brew install weasyprint
# Ref: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation
```

## Usage

All project-specific files are managed within the `projects` directory. Each project has its own subdirectory containing `origin_files`, `md_files`, `processed`, and `translated` directories, along with a `glossary.json` file.

**Processors:**

1. If the original files are markdown, just put them in the `md_files` folder.
2. If the original files are PDF, EPUB, or DOCX, put them in the `origin_files` folder and run the `mdfy` command to convert them to markdown.
3. When files are ready in the `md_files` folder, run the `translate` command to translate them. When translate is done, the markdown files will be in the `processed` directory.
4. When translated files are ready, you can run the `output` command to generate output files (PDF or other supported formats) to the `processed` directory.

### Translate

Translate Markdown files within a specified project.

**Basic Usage:**

```bash
poetry run my-tm translate <project_name> [OPTIONS]
```

Or:

```bash
my-tm translate <project_name> [OPTIONS]
```

**Options:**

- `--chunk-size INTEGER`: Set the size of each chunk in characters. Default is `4000`.
- `--overlap INTEGER`: Set the overlap between chunks in characters. Default is `0`.
- `--auto-index`: Enable automatic book_info indexing and updating.
- `--custom-prompt`: Custom prompt for LLM.

**Example:**

```bash
poetry run my-tm translate my_project --chunk-size 5000 --overlap 100 --auto-index --custom-prompt "あなたは英語から日本語への翻訳専門家であり、本の一部を翻訳する役割を担っています。翻訳には純粋なテキストのみを返し、追加の説明や元の内容以外の情報は含めないでください。[[[ ]]]の中のテキストは変更しないでください。脚注番号もそのまま維持してください。不正確と思われるページ番号やヘッダー、フッターの情報は無視してください。"
```

*Note:* The glossary file is expected to be located at `projects/<project_name>/glossary.json`. Ensure this file exists before running the translate command.

### Mdfy

Convert PDF, EPUB, or DOCX files to Markdown format within a specified project.

**Basic Usage:**

```bash
poetry run my-tm mdfy <project_name>
```

Or:

```bash
my-tm mdfy <project_name>
```

**Options:**

- Currently, no additional options. The command uses default directories within the project.

**Examples:**

1. **Using default project directories:**

    ```bash
    poetry run my-tm mdfy my_project
    ```

    This command will read all supported PDF, EPUB, or DOCX files from the `projects/my_project/origin_files` directory, convert them to Markdown format, and save the results to the `projects/my_project/md_files` directory.

### Output

Generate output from translated Markdown files within a specified project.

**Basic Usage:**

```bash
poetry run my-tm output <project_name> [OPTIONS]
```

Or:

```bash
my-tm output <project_name> [OPTIONS]
```

**Options:**

- `--output TEXT`: Name of the output file (without extension). Default is `translated_output`.
- `--type {pdf}`: Type of output to generate. Currently, only PDF is supported.
- `--bilingual {none,side-by-side,alternate-pages}`: Bilingual output mode. Default is `none`.

**Example:**

```bash
poetry run my-tm output my_project --output translated_example --type pdf --bilingual side-by-side
```

*Note:* This command processes all files located in the `projects/<project_name>/processed` directory. Ensure that the `processed` directory contains the files you wish to convert before running this command.

### Test Load Environment

After installation, verify that environment variables are correctly loaded.

```bash
poetry run my-tm test-load-env
```

Or, if you're in an activated Poetry shell:

```bash
my-tm test-load-env
```

## Detailed Description

### Project Directory Structure

Each project should have its own directory within the `projects` folder. The structure is as follows:

```
projects/
├── <project_name>/
│   ├── origin_files/    # Contains PDF, EPUB, or DOCX files
│   ├── md_files/        # Contains converted Markdown files
│   ├── processed/       # Contains processed and translated files
│   ├── glossary.json    # Glossary file for translations
│   └── README.md        # Project-specific README
```

### Translate Command

The `translate` command processes Markdown files for translation within the specified project. It splits the Markdown content into manageable chunks, applies dictionary-based translations using the `glossary.json` file, and utilizes an AI translation agent to translate the content. The process ensures efficient handling of large documents and maintains the structure and formatting of the original Markdown files.

#### Processing Steps

1. **Split Markdown Files:**
    - The tool splits large Markdown files into smaller chunks based on the specified `chunk_size` and `overlap`.

2. **Dictionary Translation:**
    - Applies translations using the `glossary.json` file to ensure consistent terminology across the document.

3. **AI Translation:**
    - Utilizes an AI translation agent to translate the split chunks, ensuring high-quality translations.
    - If `auto-index` is enabled, it automatically updates book_info indexing.

4. **Save Results:**
    - Saves the processed and translated files to the `processed` directory within the project.

### Mdfy Command

The `mdfy` command converts PDF, EPUB, or DOCX files into Markdown format within the specified project. It processes the text to remove unwanted line breaks, retaining only those after periods to maintain paragraph structure. This results in clean and readable Markdown files suitable for further processing or publication.

#### Processing Steps

1. **Extract Text:**
    - For PDF files, uses `PyPDF2` to extract plain text.
    - For EPUB files, uses `ebooklib` to read and convert HTML content to plain text.
    - For DOCX files, uses `python-docx` to extract plain text.

2. **Clean Text:**
    - Removes unnecessary line breaks that are not preceded by a period.
    - Replaces multiple whitespace characters with a single space.
    - Ensures that each sentence ends with a period followed by a line break for better readability in Markdown.

3. **Convert to Markdown:**
    - Utilizes `markdownify` to convert the cleaned plain text into Markdown format.

4. **Save Result:**
    - Saves the converted Markdown content to the `md_files` directory within the project, maintaining the original file names with a `.md` extension.

### Output Command

The `output` command generates the specified output type from translated Markdown files within a project. Currently, it supports PDF generation with options for bilingual output.

#### Processing Steps

1. **Read Processed Files:**
    - Scans the `projects/<project_name>/processed` directory for all relevant files.

2. **Generate Output:**
    - For PDF output:
        - Converts the processed content into a PDF file.
        - Applies the specified bilingual mode (none, side-by-side, or alternate-pages) if requested.

3. **Save Output:**
    - Saves the generated output file in the project directory with the specified name and extension.

**Note:** If your input files include images or other assets, ensure that their paths are correctly referenced and accessible during the output generation process.

### Test Load Environment Command

The `test-load-env` command verifies that environment variables are correctly loaded and accessible within the tool. This is useful for ensuring that all necessary configurations are set before performing translations or conversions.

#### Usage

- **Command:**

    ```bash
    poetry run my-tm test-load-env
    ```

- **Functionality:**
    - Loads environment variables as defined in your configuration.
    - Logs a confirmation message upon successful loading.

**Example Output:**

```
2024-04-27 12:00:00,000 - my_tm - INFO - Environment variables loaded successfully.
```

## Development and Contribution

Contributions are welcome! Please submit Issues or Pull Requests to propose improvements or fix bugs.

## License

All rights reserved.