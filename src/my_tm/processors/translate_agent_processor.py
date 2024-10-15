from typing import List, Tuple, Dict, Optional, Any
from typing_extensions import TypedDict
import re
import json
import os

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from langgraph.graph import StateGraph, END, START

from my_tm.processors.state_management_base import StateManagementBase
from my_tm.utils.data_utils import load_json
from my_tm.config.logger import logger
from my_tm.config.env import env_config
from my_tm.utils.file_utils import save_file
from my_tm.models.chunk_model import (
    ProgressEnum,
)

base_prompt_str = """
您是一位專精於從英語翻譯成繁體中文（臺灣使用）的語言學專家，負責翻譯一本書中的一小部分。請確保所有翻譯均使用繁體中文字符（繁體字），並且不要使用任何簡體中文字符（簡體字）。某些術語已預先翻譯並括在方括號中。請參考提供的術語詞彙表 JSON 文件進行翻譯。翻譯時，只返回純文本翻譯，不要添加任何額外的解釋或非原文內容。使用標準的臺灣術語和標點符號，包括使用「」來表示引用，而不是 "" 或 ''。不要更改 [[[ ]]] 括號內的任何文字。保留腳註編號。如果您遇到任何看起來不正確的分頁信息、頁首或頁尾，請忽略它們。
"""

# Define prompt templates
initial_translation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """{custum_prompt}如果原文中有雜亂的換行或段落，請將它們重新排列成邏輯且易讀的片段。如果原始結構已經合乎邏輯，請不要更改。

請使用適當的 markdown 語法格式化翻譯內容，包括表格、標題和其他必要的 markdown 元素，但**不要添加任何超出原文的額外內容**。僅在適當的地方對翻譯文本應用 markdown。

<GLOSSARY_JSON>{glossary_json}</GLOSSARY_JSON>

<BOOK_INFO>{book_info}</BOOK_INFO>""",
        ),
        ("human", "{input}"),
    ]
)


reflection_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """{custum_prompt}""",
        ),
        (
            "human",
            """<SOURCE_TEXT>
{source_text}
</SOURCE_TEXT>

<TRANSLATION>
{initial_translation}
</TRANSLATION>

請提供建設性的反饋和建議，以改進上述翻譯，包括對換行和段落結構適當性的評論。請以 markdown 格式組織您的回應。""",
        ),
    ]
)


improvement_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """{custum_prompt}返回的文本應僅包含翻譯，不應添加任何其他內容或標記。""",
        ),
        (
            "human",
            """<SOURCE_TEXT>
{source_text}
</SOURCE_TEXT>

<TRANSLATION>
{initial_translation}
</TRANSLATION>

<FEEDBACK>
{feedback}
</FEEDBACK>

請根據以上反饋提供改進的翻譯，確保換行和段落合乎邏輯且易讀。以 markdown 格式結構化翻譯。返回的文本應僅包含翻譯，不應添加任何其他內容或標記。""",
        ),
    ]
)


update_book_info_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """您是一位對書籍結構、風格和多語種翻譯有深入了解的語言學專家。請確保所有輸出均使用繁體中文字符（繁體字），並且不要使用任何簡體中文字符（簡體字）。您的任務是根據現有信息和新的文本片段提供更新後的 book_info。book_info 應該是一個全面的、完整的 JSON 對象，包含：
1. 從舊 book_info 所進行的調整結果。
2. 對書籍風格和體裁的當前理解。
3. 書名。
4. 來自提供的文本片段的新訊息。
5. 可能需要翻譯的術語（專有名詞或術語）的新詞彙表部分。

更新時：
- 從舊 book_info 的完整結構開始。
- 參考在 glossary_json 中的詞彙表來工作，但不要將詞彙表中的語詞添加到 book_info 中。
- 如果本片段對風格、體裁或書名提供了新的見解，請相應更新這些字段。
- 如果文本片段不包含任何新的信息，返回未修改的現有 book_info。
- 確保更新的 book_info 完整地表示了關於該書的所有已知信息，包括舊的和新的數據。舊的數據必須包含在傳回的數據中。
- 在將術語添加到詞彙表時，請以雙語格式（例如，中文和英文）提供原始術語及其翻譯。
- 不要包含任何註釋、解釋或其他文本——只返回完整的 JSON 對象。

<GLOSSARY_JSON>{glossary_json}</GLOSSARY_JSON>
<OLD_BOOK_INFO>
{old_book_info}
</OLD_BOOK_INFO>
<CHUNK>
{chunk}
</CHUNK>

請僅以 JSON 格式提供完整、更新的 book_info，包含全書完整信息、來自文本片段的任何新細節，以及詞彙表部分中術語和名稱的相關翻譯。""",
        ),
        ("human", ""),
    ]
)


# Define data model for agent state
class AgentState(TypedDict):
    content: str
    glossary_json: str
    source_text: str
    initial_translation: Optional[str]
    feedback: Optional[str]
    improved_translation: Optional[str]
    book_info: str
    usage_translate: Optional[Dict[str, Any]]
    usage_reflect: Optional[Dict[str, Any]]
    usage_improve: Optional[Dict[str, Any]]
    usage_book_info: Optional[Dict[str, Any]]


# Define the translation processor class using LangGraph
class TranslateAgentProcessor(StateManagementBase):
    """
    Class responsible for translating text chunks using a language model-based approach.
    It processes files that have been dictionary translated (state is DICTION_TRANSLATED),
    applies LLM translations to each chunk, updates the 'improve_translated' field,
    and updates the file's progress state.
    """

    def __init__(
        self,
        processed_directory: str,
        glossary_path: str,
        auto_index: bool = False,
        state_file: str = "process_state.json",
        custom_prompt: str = base_prompt_str,
    ):
        """
        Initialize the TranslateAgentProcessor with necessary parameters.

        Args:
            processed_directory (str): The directory path where the processed JSON files are saved.
            glossary_path (str): The path to the JSON file containing the translation dictionary.
            auto_index (bool): Whether to automatically update book_info. Default is False.
            state_file (str): The filename for storing the unified process state. Default is "process_state.json".
        """
        super().__init__(processed_directory, state_file)

        self.processed_directory = processed_directory
        self.auto_index = auto_index
        self.state_file_path = os.path.join(self.processed_directory, state_file)
        self.glossary_path = glossary_path
        self.custom_prompt = custom_prompt

        # Load the translation dictionary
        self.translation_dict = self._load_translation_dict()

        # Initialize the language model
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            openai_api_key=env_config["OPENAI_API_KEY"],
        )

        # Create the translation workflow graph
        self.graph = self.create_translation_graph()

        # Define pricing
        self.input_price_per_million_tokens = 0.150
        self.output_price_per_million_tokens = 0.600

        self.total_cost = 0
        self.total_tokens = 0

    def _load_translation_dict(self) -> Dict[str, str]:
        """
        Load the translation dictionary from the specified JSON file.

        Returns:
            Dict[str, str]: The translation dictionary.
        """
        try:
            translation_dict = load_json(self.glossary_path)
            return translation_dict
        except Exception as e:
            logger.error(
                f"Failed to load translation dictionary from '{self.glossary_path}': {e}"
            )
            raise

    def create_translation_graph(self) -> StateGraph:
        """
        Creates the translation workflow graph based on the auto_index parameter.

        Returns:
            StateGraph: The compiled translation graph.
        """
        workflow = StateGraph(AgentState)

        workflow.add_node("update_book_info", self.update_book_info)
        workflow.add_node("translate", self.translate)
        workflow.add_node("reflect", self.reflect)
        workflow.add_node("improve", self.improve)

        workflow.add_edge(START, "update_book_info")
        workflow.add_edge("update_book_info", "translate")
        workflow.add_edge("translate", "reflect")
        workflow.add_edge("reflect", "improve")
        workflow.add_edge("improve", END)

        return workflow.compile()

    def translate(self, state: AgentState) -> Dict[str, Any]:
        """
        Performs the initial translation.

        Args:
            state (AgentState): The current state containing 'content', 'glossary_json', and 'book_info'.

        Returns:
            Dict[str, Any]: Updated state with 'initial_translation' and 'usage'.
        """
        content = state["content"]
        glossary_json = state["glossary_json"]
        book_info = state["book_info"]

        logger.debug(
            f"Translating content: {content[:50]}..."  # Log first 50 chars for brevity
        )

        prompt = initial_translation_prompt

        messages = prompt.format_messages(
            input=content,
            glossary_json=glossary_json,
            book_info=book_info,
            custum_prompt=self.custom_prompt,
        )

        response = self.model.invoke(messages)
        return {
            "initial_translation": response.content,
            "usage_translate": response.usage_metadata,
        }

    def reflect(self, state: AgentState) -> Dict[str, Any]:
        """
        Evaluates the initial translation and provides feedback.

        Args:
            state (AgentState): The current state containing 'source_text' and 'initial_translation'.

        Returns:
            Dict[str, Any]: Updated state with 'feedback' and 'usage'.
        """
        source_text = state["source_text"]
        initial_translation = state["initial_translation"]

        logger.debug(
            f"Reflecting on translation: {initial_translation[:50]}..."  # Log first 50 chars
        )

        messages = reflection_prompt.format_messages(
            source_text=source_text,
            initial_translation=initial_translation,
            custum_prompt=self.custom_prompt,
        )
        response = self.model.invoke(messages)
        return {"feedback": response.content, "usage_reflect": response.usage_metadata}

    def improve(self, state: AgentState) -> Dict[str, Any]:
        """
        Improves the initial translation based on feedback.

        Args:
            state (AgentState): The current state containing 'source_text', 'initial_translation', and 'feedback'.

        Returns:
            Dict[str, Any]: Updated state with 'improved_translation' and 'usage'.
        """
        source_text = state["source_text"]
        initial_translation = state["initial_translation"]
        feedback = state["feedback"]

        logger.debug(
            f"Improving translation based on feedback: {feedback[:50]}..."  # Log first 50 chars
        )

        messages = improvement_prompt.format_messages(
            source_text=source_text,
            initial_translation=initial_translation,
            feedback=feedback,
            custum_prompt=self.custom_prompt,
        )
        response = self.model.invoke(messages)
        return {
            "improved_translation": response.content,
            "usage_improve": response.usage_metadata,
        }

    def update_book_info(self, state: AgentState) -> Dict[str, Any]:
        """
        Updates the book_info based on the current text chunk using Langchain.
        Args:
            state (AgentState): The current state containing 'content' and 'book_info'.
        Returns:
            Dict[str, Any]: Updated state with 'book_info' and 'usage'.
        """
        content = state["content"]
        old_book_info = state["book_info"]

        # Create a JsonOutputParser
        messages = update_book_info_prompt.format_messages(
            old_book_info=old_book_info,
            chunk=content,
            glossary_json=state["glossary_json"],
        )
        json_parser = JsonOutputParser()
        response = self.model.invoke(messages)
        new_book_info = json_parser.parse(response.content)

        save_file(
            self.processed_directory,
            "updated_book_info.json",
            json.dumps(new_book_info, indent=2),
        )

        return {"book_info": new_book_info, "usage_book_info": response.usage_metadata}

    def process(self) -> List[Tuple[str, str]]:
        """
        Processes all files in the processed directory and saves the translated content.

        Returns:
            List[Tuple[str, str]]: List of tuples containing filename and translated content.
        """
        processed_contents = []
        grouped_chunks = self._group_chunks_by_filename()

        for output_filename, chunks in grouped_chunks.items():
            logger.info(f"Processing {output_filename}")

            # Initialize book_info for each file if auto_index is True
            book_info = self._initialize_book_info(self.auto_index)

            for chunk in chunks:
                # Modification: Process chunks where 'improve_translated' is None or '[Translation Error]'
                if (
                    chunk.get("improve_translated") is not None
                    and chunk.get("improve_translated") != "[Translation Error]"
                ):
                    logger.debug(
                        f"Chunk {chunk['index']} of {output_filename} already translated. Skipping."
                    )
                    continue  # Skip this chunk as it's already translated

                try:
                    # Prepare state as a dictionary
                    state = {
                        "content": chunk.get("diction_translated", ""),
                        "glossary_json": self.translation_dict,
                        "source_text": chunk["content"],
                        "book_info": book_info,
                    }

                    # Execute LangGraph
                    results = self.graph.invoke(state)

                    # Update book_info if it was modified
                    if self.auto_index:
                        book_info = results.get("book_info", book_info)

                    improved_translation = results.get("improved_translation")
                    usage_translate = results.get("usage_translate", {})
                    usage_reflect = results.get("usage_reflect", {})
                    usage_improve = results.get("usage_improve", {})
                    usage_book_info = results.get("usage_book_info", {})

                    total_input_tokens = (
                        usage_translate.get("input_tokens", 0)
                        + usage_reflect.get("input_tokens", 0)
                        + usage_improve.get("input_tokens", 0)
                        + usage_book_info.get("input_tokens", 0)
                    )

                    total_output_tokens = (
                        usage_translate.get("output_tokens", 0)
                        + usage_reflect.get("output_tokens", 0)
                        + usage_improve.get("output_tokens", 0)
                        + usage_book_info.get("output_tokens", 0)
                    )

                    cost = self._gen_cost(
                        {
                            "input_tokens": total_input_tokens,
                            "output_tokens": total_output_tokens,
                        }
                    )

                    self.total_tokens += total_input_tokens + total_output_tokens
                    self.total_cost += cost

                    if not improved_translation:
                        raise ValueError(
                            "No improved_translation found in the workflow output."
                        )

                    # Update the chunk's improve_translated field
                    chunk["improve_translated"] = improved_translation

                    logger.info(
                        f"Successfully translated chunk from {output_filename} (Index: {chunk['index'] + 1}/{chunk['total']}). Tokens: {total_input_tokens + total_output_tokens}, Cost: ${cost:.4f}"
                    )

                    # Update the state
                    file_state = self.state.get_file_by_name(output_filename)
                    if file_state:
                        # Update the specific chunk
                        for file_chunk in file_state.chunks:
                            if file_chunk.index == chunk["index"]:
                                cleaned_improved_translation = re.sub(
                                    r"\[\[\[(.*?)\]\]\]", r"\1", improved_translation
                                )
                                file_chunk.improve_translated = (
                                    cleaned_improved_translation
                                )
                                break
                        # Save the updated state
                        self._save_state(self.state)
                        logger.debug(
                            f"State saved after processing chunk {chunk['index']} of {output_filename}."
                        )

                except Exception as e:
                    logger.error(
                        f"Error translating chunk {chunk['index']} of {output_filename}: {e}"
                    )
                    chunk["improve_translated"] = "[Translation Error]"
                    # Even if there's an error, save the state to mark this chunk as errored
                    file_state = self.state.get_file_by_name(output_filename)
                    if file_state:
                        for file_chunk in file_state.chunks:
                            if file_chunk.index == chunk["index"]:
                                file_chunk.improve_translated = "[Translation Error]"
                                break
                        self._save_state(self.state)
                        logger.debug(
                            f"State saved after error in chunk {chunk['index']} of {output_filename}."
                        )

            # After all chunks in the file are processed, update the file's progress
            file_state = self.state.get_file_by_name(output_filename)
            if file_state:
                file_state.progress = ProgressEnum.LLM_TRANSLATED
                self._save_state(self.state)
                logger.info(f"Successfully processed and updated {output_filename}")

            processed_contents.append((output_filename, ""))

        logger.info(f"Total tokens used: {self.total_tokens}")
        logger.info(f"Total cost for all translations: ${self.total_cost:.4f}")
        return processed_contents

    def _group_chunks_by_filename(self) -> Dict[str, List[Dict]]:
        """
        Groups chunks by their original filename.

        Returns:
            Dict[str, List[Dict]]: Dictionary mapping filenames to their respective chunks.
        """
        grouped_chunks = {}
        for file_data in self.state.files:
            original_filename = file_data.filename
            if original_filename not in grouped_chunks:
                grouped_chunks[original_filename] = []
            grouped_chunks[original_filename].extend(
                [chunk.model_dump() for chunk in file_data.chunks]
            )
        return grouped_chunks

    def _gen_cost(self, usage: Dict[str, Any]) -> float:
        """
        Calculates the cost of a given usage.

        Args:
            usage (Dict[str, Any]): The usage dictionary.

        Returns:
            float: The cost of the usage.
        """
        return (
            usage.get("input_tokens", 0)
            * self.input_price_per_million_tokens
            / 1_000_000
            + usage.get("output_tokens", 0)
            * self.output_price_per_million_tokens
            / 1_000_000
        )

    def _initialize_book_info(self, auto_index: bool) -> str:
        """
        Initializes the book_info with default values.

        Returns:
            str: The initial book_info JSON string.
        """

        initial_book_info = {
            "book_title": "[Update it based on the title of the book]",
            "style": "[Update it based on the style of the book]",
            "genre": "[Update it based on the genre of the book]",
            "glossary": {
                "[TERM]": "[詞項翻譯]",
            },
        }
        return json.dumps(initial_book_info, ensure_ascii=False)
