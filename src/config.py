"""
Configuration classes for RAGAnything

Contains configuration dataclasses with environment variable support
"""

from dataclasses import dataclass, field
from typing import List
from lightrag.utils import get_env_value


@dataclass
class RAGAnythingConfig:
    """
    ---
    NOTE
    ---
    Configuration class for RAGAnything with environment variable support.
        NOTE Directory Configuration
            1. working_dir:                         Directory where RAG storage and cache files are stored.
        NOTE Parser Configuration
            2. parse_method:                        Default parsing method for document parsing: 'auto', 'ocr', or 'txt'.
            3. parser_output_dir:                   Default output directory for parsed content.
            4. parser:                              Parser selection: 'mineru' or 'docling'.
            5. display_content_stats:               Whether to display content statistics during parsing.
        NOTE Multimodal Processing Configuration
            6. enable_image_processing:             Whether to enable image content processing.
            7. enable_table_processing:             Whether to enable table content processing.
            8. enable_equation_processing:          Whether to enable equation content processing.
        NOTE Batch Processing Configuration
            9. max_concurrent_files:                Maximum number of files to process concurrently.
            10. supported_file_extensions:          List of supported file extensions for batch processing.
            11. recursive_folder_processing:        Whether to recursively process subfolders in batch mode.
        NOTE Context Extraction Configuration
            12. context_window:                     Number of pages/chunks to include before and after current item for context.
            13. context_mode:                       Context extraction mode: 'page' for page-based, 'chunk' for chunk-based.
            14. max_context_tokens:                 Maximum number of tokens in extracted context.
            15. include_headers:                    Whether to include document headers and titles in context.
            16. include_captions:                   Whether to include image/table captions in context.
            17. context_filter_content_types:       Content types to include in context extraction (e.g., 'text', 'image', 'table').
            18. content_format:                     Default content format for context extraction when processing documents.
        NOTE Path Handling Configuration
            19. use_full_path:                      Whether to use full file path (True) or just basename (False) for file references in LightRAG.
    """
    working_dir: str = field(default=get_env_value("WORKING_DIR", "./rag_storage", str))
    
    parse_method: str = field(default=get_env_value("PARSE_METHOD", "auto", str))
    
    parser_output_dir: str = field(default=get_env_value("OUTPUT_DIR", "./output", str))
    
    parser: str = field(default=get_env_value("PARSER", "mineru", str))
    
    display_content_stats: bool = field(default=get_env_value("DISPLAY_CONTENT_STATS", True, bool))

    enable_image_processing: bool = field(default=get_env_value("ENABLE_IMAGE_PROCESSING", True, bool))
    
    enable_table_processing: bool = field(default=get_env_value("ENABLE_TABLE_PROCESSING", True, bool))
    
    enable_equation_processing: bool = field(default=get_env_value("ENABLE_EQUATION_PROCESSING", True, bool))

    max_concurrent_files: int = field(default=get_env_value("MAX_CONCURRENT_FILES", 1, int))

    supported_file_extensions: List[str] = field(default_factory=lambda: get_env_value(
            "SUPPORTED_FILE_EXTENSIONS",
            ".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.tif,.gif,.webp,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md",
            str,).split(","))
    
    recursive_folder_processing: bool = field(default=get_env_value("RECURSIVE_FOLDER_PROCESSING", True, bool))

    context_window: int = field(default=get_env_value("CONTEXT_WINDOW", 1, int))
    
    context_mode: str = field(default=get_env_value("CONTEXT_MODE", "page", str))
    
    max_context_tokens: int = field(default=get_env_value("MAX_CONTEXT_TOKENS", 2000, int))
    
    include_headers: bool = field(default=get_env_value("INCLUDE_HEADERS", True, bool))
    
    include_captions: bool = field(default=get_env_value("INCLUDE_CAPTIONS", True, bool))
    
    context_filter_content_types: List[str] = field(default_factory=lambda: get_env_value(
            "CONTEXT_FILTER_CONTENT_TYPES", "text", str).split(","))
    
    content_format: str = field(default=get_env_value("CONTENT_FORMAT", "minerU", str))

    use_full_path: bool = field(default=get_env_value("USE_FULL_PATH", False, bool))

    def __post_init__(self):
        """
        Post-initialization setup for backward compatibility
        """
        # Support legacy environment variable names for backward compatibility
        legacy_parse_method = get_env_value("MINERU_PARSE_METHOD", None, str)
        if legacy_parse_method and not get_env_value("PARSE_METHOD", None, str):
            self.parse_method = legacy_parse_method
            import warnings

            warnings.warn(
                "MINERU_PARSE_METHOD is deprecated. Use PARSE_METHOD instead.",
                DeprecationWarning,
                stacklevel=2,
            )

    @property
    def mineru_parse_method(self) -> str:
        """
        ---
        Note:
        ---
        Backward compatibility property for old code.
        deprecated::
           Use `parse_method` instead. This property will be removed in a future version.
        
        """
        import warnings

        warnings.warn(
            "mineru_parse_method is deprecated. Use parse_method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.parse_method

    @mineru_parse_method.setter
    def mineru_parse_method(self, value: str):
        """Setter for backward compatibility"""
        import warnings

        warnings.warn(
            "mineru_parse_method is deprecated. Use parse_method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.parse_method = value
