from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ProgressEnum(str, Enum):
    """
    Enum representing the possible progress states for file processing.
    """

    INIT = "init"
    SPLITED = "splited"
    DICTION_TRANSLATED = "dict_translated"
    LLM_TRANSLATED = "llm_translated"


class ChunkModel(BaseModel):
    """
    Represents a chunk of text from a file.

    Attributes:
        filename (str): Name of the file from which the chunk originates.
        content (str): Content of the chunk.
        index (int): Index of the chunk within the file.
        total (int): Total number of chunks for the file.
        diction_translated (Optional[str]): The diction-translated content of the chunk. Initially None.
        improve_translated (Optional[str]): The improved translation of the chunk. Initially None.
    """

    filename: str
    content: str
    index: int
    total: int
    diction_translated: Optional[str] = None
    improve_translated: Optional[str] = None


class FileChunksModel(BaseModel):
    """
    Represents all the chunks from a single file.

    Attributes:
        filename (str): The name of the file.
        chunks (List[ChunkModel]): List of chunks for the file.
        progress (ProgressEnum): Current progress state of the file.
    """

    filename: str
    chunks: List[ChunkModel]
    progress: ProgressEnum = Field(
        default=ProgressEnum.INIT, description="Current progress state of the file."
    )

    def get_chunk_by_index(self, chunk_index: int) -> Optional[ChunkModel]:
        """
        Retrieve a chunk by its index.

        Args:
            chunk_index (int): The index of the chunk to retrieve.

        Returns:
            Optional[ChunkModel]: The chunk if found, else None.
        """
        return next(
            (chunk for chunk in self.chunks if chunk.index == chunk_index), None
        )


class ProcessStateModel(BaseModel):
    """
    Model to manage the state of all files being processed.

    Attributes:
        files (List[FileChunksModel]): List of files and their chunks.
    """

    files: List[FileChunksModel] = []

    def get_file_by_name(self, filename: str) -> Optional[FileChunksModel]:
        """
        Retrieve a file by its name.

        Args:
            filename (str): The name of the file to retrieve.

        Returns:
            Optional[FileChunksModel]: The file if found, else None.
        """
        return next((file for file in self.files if file.filename == filename), None)

    def get_chunk(self, filename: str, chunk_index: int) -> Optional[ChunkModel]:
        """
        Retrieve a chunk by filename and chunk index.

        Args:
            filename (str): The name of the file.
            chunk_index (int): The index of the chunk to retrieve.

        Returns:
            Optional[ChunkModel]: The chunk if found, else None.
        """
        file = self.get_file_by_name(filename)
        if file:
            return file.get_chunk_by_index(chunk_index)
        return None
