# <Project Name>

## Project Structure

This project follows a specific directory structure to ensure proper organization and management of files. The structure is as follows:

```bash
<project_name>/
├── origin_files/    # Contains PDF, EPUB or DOCX files
├── md_files/        # Contains converted Markdown files
├── glossary.json    # Glossary file for translations
└── README.md        # Project-specific README
```

## Processors

1. If the original files are markdown, just put them in the 'md_files' folder.
2. If the original files are PDF, EPUB, or DOCX, put them in the 'origin_files' folder and run the 'mdfy' command to convert them to markdown.
