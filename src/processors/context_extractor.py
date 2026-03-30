import re
import json
import time
import base64
import doctest
from typing import Dict, Any, Tuple, List, Optional
from pathlib import Path
from dataclasses import dataclass

from lightrag.utils import logger

@dataclass
class ContextConfig:
    """Configuration for context extraction"""

    context_window:         int = 1                     # Window size for context extraction
    context_mode:           str = "page"                # "page", "chunk", "token"
    max_context_tokens:     int = 2000                  # Maximum context tokens
    include_headers:        bool = True                 # Whether to include headers/titles
    include_captions:       bool = True                 # Whether to include image/table captions
    filter_content_types:   Optional[List[str]] = None  # Content types to include

    def __post_init__(self):
        if self.filter_content_types is None:
            self.filter_content_types = ["text"]


class ContextExtractor:
    """
    Universal context extractor supporting multiple content source formats
    """

    def __init__(self, config: Optional[ContextConfig] = None, tokenizer=None):
        """
        ---
        Note:
        ---
        Initialize context extractor
        
        ---
        Args:
        ---
        config: Context extraction configuration
        tokenizer: Tokenizer for accurate token counting
        
        """
        self.config = config or ContextConfig()
        self.tokenizer = tokenizer


    def extract_context(self, content_source: Any, current_item_info: Dict[str, Any], content_format: str = "auto",) -> str:
        """
        ---
        Note:
        ---
        Extract context for current item from content source

        ---
        Args:
        ---
        content_source: Source content (list, dict, or other format)
        current_item_info: Information about current item (page_idx, index, etc.)
        content_format: Format hint for content source ("minerU", "text_chunks", "auto", etc.)

        ---
        Returns:
        ---
        Extracted context text
        
        """
        if not content_source and not self.config.context_window:
            return ""

        try:
            # Use format hint if provided, otherwise auto-detect
            if content_format == "minerU" and isinstance(content_source, list):
                return self._extract_mineru_source(content_source, current_item_info)
            
            elif content_format == "text_chunks" and isinstance(content_source, list):
                return self._extract_from_text_chunks(content_source, current_item_info)
            
            elif content_format == "text" and isinstance(content_source, str):
                return self._extract_from_text_source(content_source, current_item_info)
            
            else:
                # Auto-detect content source format
                if isinstance(content_source, list):
                    return self._extract_mineru_source(
                        content_source, current_item_info
                    )
                elif isinstance(content_source, dict):
                    return self._extract_from_dict_source(
                        content_source, current_item_info
                    )
                elif isinstance(content_source, str):
                    return self._extract_from_text_source(
                        content_source, current_item_info
                    )
                else:
                    logger.warning(
                        f"Unsupported content source type: {type(content_source)}"
                    )
                    return ""
                
        except Exception as e:
            logger.error(f"Error extracting context: {e}")
            return ""


    def _extract_mineru_source(self, content_list: List[Dict], current_item_info: Dict) -> str:
        """
        ---
        Note:
        ---
        Extract context from MinerU-style content list

        ---
        Args:
        ---
        content_list: List of content items with page_idx and type info
        current_item_info: Current item information

        ---
        Returns:
        ---
        Context text from surrounding pages/chunks
        
        """
        if self.config.context_mode == "page":
            return self.__extract_page_context(content_list, current_item_info)
        elif self.config.context_mode == "chunk":
            return self.__extract_chunk_context(content_list, current_item_info)
        else:
            return self.__extract_page_context(content_list, current_item_info)


    def __extract_page_context(self, content_list: List[Dict], current_item_info: Dict) -> str:
        """
        ---
        Note:
        ---
        Extract context based on page boundaries

        ---
        Args:
        ---
        content_list: List of content items
        current_item_info: Current item with page_idx

        ---
        Returns:
        ---
        Context text from surrounding pages
        
        ---
        Tests:
        ---
        >>> config = ContextConfig()
        >>> extractor = ContextExtractor(config)
        >>> extractor.config.max_context_tokens = 50
        >>> extractor.config.context_window = 1

        >>> content_list = [
        ...     {"page_idx": 0, "type": "text", "text": "Sample text 0", "text_level": 1},
        ...     {"page_idx": 1, "type": "text", "text": "Sample text 1", "text_level": 0},
        ...     {"page_idx": 2, "type": "text", "text": "Sample text 2", "text_level": 0},
        ...     {"page_idx": 3, "type": "text", "text": "Sample text 3", "text_level": 0}
        ... ]
        >>> print(extractor._ContextExtractor__extract_page_context(content_list, content_list[1]))
        [Page 0] # Sample text 0
        Sample text 1
        [Page 2] Sa...

        """
        current_page = current_item_info.get("page_idx", 0)
        window_size = self.config.context_window

        start_page = max(0, current_page - window_size)
        end_page = current_page + window_size + 1

        context_texts = []

        for item in content_list:
            item_page = item.get("page_idx", 0)
            item_type = item.get("type", "")

            # Check if item is within context window and matches filter criteria
            if (start_page <= item_page < end_page and item_type in self.config.filter_content_types):
                text_content = self.__extract_text_from_item(item)
                if text_content and text_content.strip():
                    # Add page marker for better context understanding
                    if item_page != current_page:
                        context_texts.append(f"[Page {item_page}] {text_content}")
                    else:
                        context_texts.append(text_content)

        context = "\n".join(context_texts)
        return self._truncate_context(context)


    def __extract_chunk_context(self, content_list: List[Dict], current_item_info: Dict) -> str:
        """
        ---
        Note:
        ---
        Extract context based on content chunks

        ---
        Args:
        ---
        content_list: List of content items
        current_item_info: Current item with index info

        ---
        Returns:
        ---
        Context text from surrounding chunks
        
        ---
        Tests:
        ---
        >>> config = ContextConfig()
        >>> extractor = ContextExtractor(config)
        >>> extractor.config.max_context_tokens = 50
        >>> extractor.config.context_window = 1

        >>> content_list = [
        ...     {"index": 0, "type": "text", "text": "Sample text 0", "text_level": 1},
        ...     {"index": 1, "type": "text", "text": "Sample text 1", "text_level": 0},
        ...     {"index": 2, "type": "text", "text": "Sample text 2", "text_level": 0},
        ...     {"index": 3, "type": "text", "text": "Sample text 3", "text_level": 0}
        ... ]
        >>> print(extractor._ContextExtractor__extract_chunk_context(content_list, content_list[1]))
        # Sample text 0
        # Sample text 0
        Sample text 2

        """
        current_index = current_item_info.get("index", 0)
        window_size = self.config.context_window

        start_idx = max(0, current_index - window_size)
        end_idx = min(len(content_list), current_index + window_size + 1)

        context_texts = []

        for i in range(start_idx, end_idx):
            if i != current_index:
                item = content_list[i]
                item_type = item.get("type", "")

                if item_type in self.config.filter_content_types:
                    text_content = self.__extract_text_from_item(item)
                    if text_content and text_content.strip():
                        context_texts.append(text_content)
            else:
                context_texts.append(self.__extract_text_from_item(item))

        context = "\n".join(context_texts)
        return self._truncate_context(context)


    def __extract_text_from_item(self, item: Dict) -> str:
        """
        ---
        Note:
        ---
        Extract text content from a content item

        ---
        Args:
        ---
        item: Content item dictionary

        ---
        Returns:
        ---
        Extracted text content
        
        ---
        Tests:
        ---
        >>> extractor = ContextExtractor()
        
        >>> item = {"type": "text", "text": "Sample text", "text_level": 1}
        >>> extractor._ContextExtractor__extract_text_from_item(item)
        '# Sample text'
        
        >>> item = {"type": "image", "image_caption": ["Sample image caption"]}
        >>> extractor._ContextExtractor__extract_text_from_item(item)
        '[Image: Sample image caption]'
        
        >>> item = {"type": "table", "table_caption": ["Sample table caption"]}
        >>> print(extractor._ContextExtractor__extract_text_from_item(item))
        [Table: Sample table caption]
        """
        item_type = item.get("type", "")

        if item_type == "text":
            text = item.get("text", "")
            text_level = item.get("text_level", 0)

            # Add header indication for structured content
            if self.config.include_headers and text_level > 0:
                return f"{'#' * text_level} {text}"
            return text
        
        elif item_type == "image" and self.config.include_captions:
            captions = item.get("image_caption", item.get("img_caption", []))
            if captions:
                return f"[Image: {', '.join(captions)}]"

        elif item_type == "table" and self.config.include_captions:
            captions = item.get("table_caption", [])
            if captions:
                return f"[Table: {', '.join(captions)}]"

        return ""


    def _extract_from_dict_source(self, dict_source: Dict, current_item_info: Dict) -> str:
        """
        ---
        Note:
        ---
        Extract context from dictionary-based content source

        ---
        Args:
        ---
        dict_source: Dictionary containing content
        current_item_info: Current item information

        ---
        Returns:
        ---
        Extracted context text
        """
        # Handle different dictionary structures
        if "content" in dict_source:
            context = str(dict_source["content"])
        elif "text" in dict_source:
            context = str(dict_source["text"])
        else:
            # Try to extract any string values
            text_parts = []
            for value in dict_source.values():
                if isinstance(value, str):
                    text_parts.append(value)
            context = "\n".join(text_parts)

        return self._truncate_context(context)


    def _extract_from_text_source(self, text_source: str, current_item_info: Dict) -> str:
        """Extract context from plain text source

        Args:
            text_source: Plain text content
            current_item_info: Current item information

        Returns:
            Truncated text context
        """
        return self._truncate_context(text_source)


    def _extract_from_text_chunks(self, text_chunks: List[str], current_item_info: Dict) -> str:
        """
        ---
        Note:
        ---
        Extract context from simple text chunks list

        ---
        Args:
        ---
        text_chunks: List of text strings
        current_item_info: Current item information with index

        ---
        Returns:
        ---
        Context text from surrounding chunks
        
        """
        current_index = current_item_info.get("index", 0)
        window_size = self.config.context_window

        start_idx = max(0, current_index - window_size)
        end_idx = min(len(text_chunks), current_index + window_size + 1)

        context_texts = []
        for i in range(start_idx, end_idx):
            if i != current_index:  # Exclude current chunk
                if i < len(text_chunks):
                    chunk_text = str(text_chunks[i]).strip()
                    if chunk_text:
                        context_texts.append(chunk_text)

        context = "\n".join(context_texts)
        return self._truncate_context(context)


    def _truncate_context(self, context: str) -> str:
        """
        ---
        Note:
        ---
        Truncate context to maximum token limit

        ---
        Args:
        ---
        context: Context text to truncate

        ---
        Returns:
        ---
        Truncated context text
        
        ---
        Test:
        ---
        >>> config = ContextConfig()
        >>> extractor = ContextExtractor(config)
        >>> extractor.config.max_context_tokens = 50
        
        >>> context = "This is a test context that is quite long, so it needs to be truncated."
        >>> print(extractor._truncate_context(context))
        This is a test context that is quite long, so it n...
        
        >>> context = "This is a test context that is quite long. So it needs to be truncated."
        >>> print(extractor._truncate_context(context))
        This is a test context that is quite long.
        
        """
        if not context:
            return ""

        # Use tokenizer if available for accurate token counting
        if self.tokenizer:
            tokens = self.tokenizer.encode(context)
            if len(tokens) <= self.config.max_context_tokens:
                return context

            # Truncate to max tokens and decode back to text
            truncated_tokens = tokens[: self.config.max_context_tokens]
            truncated_text = self.tokenizer.decode(truncated_tokens)

            # Try to end at a sentence boundary
            last_period = truncated_text.rfind(".")
            last_newline = truncated_text.rfind("\n")

            if last_period > len(truncated_text) * 0.8:
                return truncated_text[: last_period + 1]
            elif last_newline > len(truncated_text) * 0.8:
                return truncated_text[:last_newline]
            else:
                return truncated_text + "..."
        else:
            # Fallback to character-based truncation if no tokenizer
            if len(context) <= self.config.max_context_tokens:
                return context

            # Simple truncation - fallback when no tokenizer available
            truncated = context[: self.config.max_context_tokens]

            # Try to end at a sentence boundary
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")

            if last_period > len(truncated) * 0.8:
                return truncated[: last_period + 1]
            elif last_newline > len(truncated) * 0.8:
                return truncated[:last_newline]
            else:
                return truncated + "..."
            
if __name__ == "__main__":
    doctest.testmod(verbose=True)