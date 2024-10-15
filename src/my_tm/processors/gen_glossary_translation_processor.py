from typing import Dict, List, Tuple
import os
import json
from pydantic import BaseModel, ValidationError
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from my_tm.config.logger import logger
from my_tm.config.env import env_config
from my_tm.processors.text_split_processor import TextSplitProcessor


# Define the Pydantic model for the glossary
class GlossaryEntry(BaseModel):
    term: str
    translation: str


class Glossary(BaseModel):
    entries: Dict[str, str]


# Define the optimized translation prompt for a terminology expert
translation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an expert linguist and terminologist specializing in translation from English to Traditional Chinese. Your task is to identify any new or specialized terms in the provided text that are not present in the existing terminology glossary. For each identified term, provide its corresponding Traditional Chinese translation.

**Instructions**:
1. Review the text and compare it against the existing glossary.
2. Identify any terms that are not in the glossary.
3. For each new term, provide the term in English and its translation in Traditional Chinese.
4. Only include necessary terms and proper nouns. Do not add irrelevant or excessive terms.
5. If there are no new terms, return an empty JSON object.

**Example Output**:
```json
{
    "Machine Learning": "機器學習",
    "Neural Network": "神經網絡"
}
```""",
        ),
        (
            "human",
            """
<TEXT>
{text}
</TEXT>

<CURRENT_GLOSSARY>
{glossary_json}
</CURRENT_GLOSSARY>

Identify and translate any new or specialized terms not present in the current glossary.""",
        ),
    ]
)


class GenGlossaryTranslationProcessor:
    def __init__(
        self,
        input_directory: str,
        output_file: str,
        chunk_size: int,
        overlap: int,
    ):
        self.input_directory = input_directory
        self.output_file = output_file
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.processed_data = self._split_markdown()
        self.glossary = Glossary(entries={})
        self.total_cost = 0.0
        self.total_tokens = 0
        # Define pricing for gpt-4o-mini
        self.input_price_per_million_tokens = 0.150
        self.output_price_per_million_tokens = 0.600

        # Initialize LangChain Model
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            openai_api_key=env_config["OPENAI_API_KEY"],
        )

    def process_directory(self):
        unique_terms = self._extract_unique_terms()

        for idx, term in enumerate(unique_terms, 1):
            try:
                translation, tokens, cost = self._translate_term(term)
                self.glossary.entries[term] = translation
                logger.info(
                    f"Translated ({idx}/{len(unique_terms)}): '{term}' -> '{translation}' | Tokens: {tokens}, Cost: ${cost:.6f}"
                )
            except Exception as e:
                logger.error(f"Error translating term '{term}': {e}")
                self.glossary.entries[term] = ""  # Placeholder for failed translations

        # Validate the glossary using Pydantic
        try:
            self.glossary = Glossary(**self.glossary.model_dump())
        except ValidationError as ve:
            logger.error(f"Glossary validation error: {ve}")
            raise ve

        # Save the glossary JSON
        self._save_glossary()

        logger.info(f"Total tokens used: {self.total_tokens}")
        logger.info(f"Total cost for glossary translations: ${self.total_cost:.6f}")

    def _extract_unique_terms(self) -> List[str]:
        """
        Extracts unique terms from the processed markdown data.
        Assumes terms are defined as capitalized words.
        Modify this method based on your specific criteria for term extraction.
        """
        terms = set()
        for file_data in self.processed_data.values():
            for chunk in file_data["chunks"]:
                content = chunk["content"]
                # Simple extraction: words that start with a capital letter
                words = content.split()
                capitalized_words = {
                    word.strip(".,;:!()[]{}<>") for word in words if word.istitle()
                }
                terms.update(capitalized_words)
        return list(terms)

    def _translate_term(self, term: str) -> Tuple[str, int, float]:
        """
        Translates a single term using the LLM.
        Returns the translated term, number of tokens used, and cost.
        """
        messages = translation_prompt.format_messages(term=term)
        response = self.model.invoke(messages)
        translation = response.content.strip()

        # Assuming response has usage metadata
        usage = response.usage_metadata
        cost = (
            usage["input_tokens"] * self.input_price_per_million_tokens / 1_000_000
            + usage["output_tokens"] * self.output_price_per_million_tokens / 1_000_000
        )
        tokens = usage["total_tokens"]

        self.total_tokens += tokens
        self.total_cost += cost

        return translation, tokens, cost

    def _save_glossary(self):
        """
        Saves the glossary to the specified output file in JSON format.
        """
        output_dir = os.path.dirname(self.output_file)
        os.makedirs(output_dir, exist_ok=True)
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(
                self.glossary.model_dump()["entries"], f, ensure_ascii=False, indent=4
            )
        logger.info(f"Glossary JSON saved at {self.output_file}")
