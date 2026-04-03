import re
import json
import time
from typing import Dict, Any, Tuple, List, Optional
from lightrag.utils import logger, compute_mdhash_id
from lightrag.lightrag import LightRAG
from dataclasses import asdict
from lightrag.kg.shared_storage import get_namespace_data, get_pipeline_status_lock
from lightrag.operate import extract_entities, merge_nodes_and_edges

# Import prompt templates
from ..utils.prompt import PROMPTS
from .context_extractor import ContextExtractor

class BaseModalProcessor:
    """Base class for modal processors"""
    # ==================== main function ====================

    def __init__(self, lightrag: LightRAG, modal_caption_func, context_extractor: Optional[ContextExtractor] = None):
        self.lightrag               = lightrag
        self.modal_caption_func     = modal_caption_func

        # Use LightRAG's storage instances
        self.text_chunks_db         = lightrag.text_chunks
        self.chunks_vdb             = lightrag.chunks_vdb
        self.entities_vdb           = lightrag.entities_vdb
        self.relationships_vdb      = lightrag.relationships_vdb
        self.knowledge_graph_inst   = lightrag.chunk_entity_relation_graph

        # Use LightRAG's configuration and functions
        self.embedding_func         = lightrag.embedding_func
        self.llm_model_func         = lightrag.llm_model_func
        self.global_config          = asdict(lightrag)
        self.hashing_kv             = lightrag.llm_response_cache
        self.tokenizer              = lightrag.tokenizer

        # Initialize context extractor with tokenizer if not provided
        if context_extractor is None:
            self.context_extractor = ContextExtractor(tokenizer=self.tokenizer)
        else:
            self.context_extractor = context_extractor
            # Update tokenizer if context_extractor doesn't have one
            if self.context_extractor.tokenizer is None:
                self.context_extractor.tokenizer = self.tokenizer

        # Content source for context extraction
        self.content_source = None
        self.content_format = "auto" #  ("minerU", "text_chunks", "auto", etc.)


    def set_content_source(self, content_source: Any, content_format: str = "auto"):
        """
        ---
        Note:
        ---
        Set content source for context extraction

        ---
        Args:
        ---
            content_source: Source content for context extraction
            content_format: Format of content source ("minerU", "text_chunks", "auto")
            
        Tests:
        >>> processor = BaseModalProcessor(LightRAG, modal_caption_func)
        >>> processor.set_content_source("test content", "text_chunks")
        >>> processor.content_source
        'test content'
        >>> processor.content_format
        'text_chunks'
        """
        
        self.content_source = content_source
        self.content_format = content_format
        logger.info(f"Content source set with format: {content_format}")


    def _get_context_for_item(self, item_info: Dict[str, Any]) -> str:
        """
        ---
        Note:
        ---
        Get context for current processing item

        ---
        Args:
        ---
        item_info: Information about current item (page_idx, index, etc.)

        ---
        Returns:
        ---
        Get context for current processing item
        
        """
        if not self.content_source:
            return ""

        try:
            context = self.context_extractor.extract_context(self.content_source, item_info, self.content_format)
            # content_source better be list, so it can go to minerU branch
            if context:
                logger.debug(f"Extracted context of length {len(context)} for item: {item_info}")
            return context
        except Exception as e:
            logger.error(f"Error getting context for item {item_info}: {e}")
            return ""


    async def generate_description_only(self, modal_content, content_type: str, item_info: Optional[Dict[str, Any]] = None,
                                        entity_name: Optional[str] = None,) -> Tuple[str, Dict[str, Any]]:
        """
        ---
        Note:
        ---
        Generate text description and entity info only, without entity relation extraction.
        Used for batch processing stage 1.

        ---
        Args:
        ---
        modal_content: Modal content to process
        content_type: Type of modal content
        item_info: Item information for context extraction
        entity_name: Optional predefined entity name

        ---
        Returns:
        ---
        Tuple of (description, entity_info)
        
        """
        # Subclasses must implement this method
        raise NotImplementedError("Subclasses must implement this method")


    async def _create_entity_and_chunk(self, modal_chunk: str, entity_info: Dict[str, Any], file_path: str, batch_mode: bool = False, doc_id: Optional[str] = None, 
                                       chunk_order_index: int = 0,) -> Optional[tuple[Any, dict[str, Any], list[Any] | None]]:
        """
        ---
        Note:
        ---
        Create entity and text chunk
        """
        # Create chunk
        chunk_id = compute_mdhash_id(str(modal_chunk), prefix="chunk-")
        if self.tokenizer:
            tokens = len(self.tokenizer.encode(modal_chunk))
        else:
            raise ValueError("Tokenizer not initialized")
        
        # Use provided doc_id or generate one from chunk_id for backward compatibility
        actual_doc_id = doc_id if doc_id else chunk_id

        chunk_data = {
            "tokens": tokens,
            "content": modal_chunk,
            "chunk_order_index": chunk_order_index,
            "full_doc_id": actual_doc_id,  # Use proper document ID
            "file_path": file_path,
        }

        # Store chunk
        await self.text_chunks_db.upsert({chunk_id: chunk_data})

        # Store chunk in vector database for retrieval
        chunk_vdb_data = {
            chunk_id: {
                "content": modal_chunk,
                "full_doc_id": actual_doc_id,
                "tokens": tokens,
                "chunk_order_index": chunk_order_index,
                "file_path": file_path,
            }
        }
        await self.chunks_vdb.upsert(chunk_vdb_data)

        # Create entity node
        node_data = {
            "entity_id": entity_info["entity_name"],
            "entity_type": entity_info["entity_type"],
            "description": entity_info["summary"],
            "source_id": chunk_id,
            "file_path": file_path,
            "created_at": int(time.time()),
        }

        await self.knowledge_graph_inst.upsert_node(
            entity_info["entity_name"], node_data
        )

        # Insert entity into vector database
        entity_vdb_data = {
            compute_mdhash_id(entity_info["entity_name"], prefix="ent-"): {
                "entity_name": entity_info["entity_name"],
                "entity_type": entity_info["entity_type"],
                "content": f"{entity_info['entity_name']}\n{entity_info['summary']}",
                "source_id": chunk_id,
                "file_path": file_path,
            }
        }
        await self.entities_vdb.upsert(entity_vdb_data)

        # Process entity and relationship extraction
        chunk_results = await self._process_chunk_for_extraction(
            chunk_id, entity_info["entity_name"], batch_mode
        )

        return (
            entity_info["summary"],
            {
                "entity_name": entity_info["entity_name"],
                "entity_type": entity_info["entity_type"],
                "description": entity_info["summary"],
                "chunk_id": chunk_id,
            },
            chunk_results,
        )


    async def _process_chunk_for_extraction(self, chunk_id: str, modal_entity_name: str, batch_mode: bool = False):
        """
        Process chunk for entity and relationship extraction
        """
        
        chunk_data = await self.text_chunks_db.get_by_id(chunk_id)
        if not chunk_data:
            logger.error(f"Chunk {chunk_id} not found")
            return

        # Create text chunk for vector database
        chunk_vdb_data = {
            chunk_id: {
                "content": chunk_data["content"],
                "full_doc_id": chunk_id,
                "tokens": chunk_data["tokens"],
                "chunk_order_index": chunk_data["chunk_order_index"],
                "file_path": chunk_data["file_path"],
            }
        }

        await self.chunks_vdb.upsert(chunk_vdb_data)

        pipeline_status = await get_namespace_data("pipeline_status")
        pipeline_status_lock = get_pipeline_status_lock()

        # Prepare chunk for extraction
        chunks = {chunk_id: chunk_data}

        # Extract entities and relationships
        if chunks is None:
            raise ValueError("No chunks found for extraction")
        
        chunk_results = await extract_entities(
            chunks=chunks,  
            global_config=self.global_config,
            pipeline_status=pipeline_status,
            pipeline_status_lock=pipeline_status_lock,
            llm_response_cache=self.hashing_kv,
        )

        # Add "belongs_to" relationships for all extracted entities
        processed_chunk_results = []
        for maybe_nodes, maybe_edges in chunk_results:
            for entity_name in maybe_nodes.keys():
                if entity_name != modal_entity_name:  # Skip self-relationship
                    # Create belongs_to relationship
                    relation_data = {
                        "description": f"Entity {entity_name} belongs to {modal_entity_name}",
                        "keywords": "belongs_to,part_of,contained_in",
                        "source_id": chunk_id,
                        "weight": 10.0,
                        "file_path": chunk_data.get("file_path", "manual_creation"),
                    }
                    await self.knowledge_graph_inst.upsert_edge(
                        entity_name, modal_entity_name, relation_data
                    )

                    relation_id = compute_mdhash_id(
                        entity_name + modal_entity_name, prefix="rel-"
                    )
                    relation_vdb_data = {
                        relation_id: {
                            "src_id": entity_name,
                            "tgt_id": modal_entity_name,
                            "keywords": relation_data["keywords"],
                            "content": f"{relation_data['keywords']}\t{entity_name}\n{modal_entity_name}\n{relation_data['description']}",
                            "source_id": chunk_id,
                            "file_path": chunk_data.get("file_path", "manual_creation"),
                        }
                    }
                    await self.relationships_vdb.upsert(relation_vdb_data)

                    # Add to maybe_edges
                    maybe_edges[(entity_name, modal_entity_name)] = [relation_data]

            processed_chunk_results.append((maybe_nodes, maybe_edges))

        if not batch_mode:
            # Merge with correct file_path parameter
            file_path = chunk_data.get("file_path", "manual_creation")
            await merge_nodes_and_edges(
                chunk_results=chunk_results,
                knowledge_graph_inst=self.knowledge_graph_inst,
                entity_vdb=self.entities_vdb,
                relationships_vdb=self.relationships_vdb,
                global_config=self.global_config,
                pipeline_status=pipeline_status,
                pipeline_status_lock=pipeline_status_lock,
                llm_response_cache=self.hashing_kv,
                current_file_number=1,
                total_files=1,
                file_path=file_path,  # Pass the correct file_path
            )

            # Ensure all storage updates are complete
            await self.lightrag._insert_done()

        return processed_chunk_results

    # ==================== utils function ====================

    def _robust_json_parse(self, response: str) -> dict:
        """Robust JSON parsing with multiple fallback strategies"""

        # Strategy 1: Try direct parsing first
        for json_candidate in self._extract_all_json_candidates(response):
            result = self._try_parse_json(json_candidate)
            if result:
                return result

        # Strategy 2: Try with basic cleanup
        for json_candidate in self._extract_all_json_candidates(response):
            cleaned = self._basic_json_cleanup(json_candidate)
            result = self._try_parse_json(cleaned)
            if result:
                return result

        # Strategy 3: Try progressive quote fixing
        for json_candidate in self._extract_all_json_candidates(response):
            fixed = self._progressive_quote_fix(json_candidate)
            result = self._try_parse_json(fixed)
            if result:
                return result

        # Strategy 4: Fallback to regex field extraction
        return self._extract_fields_with_regex(response)


    def _extract_all_json_candidates(self, response: str) -> list:
        """Extract all possible JSON candidates from response"""
        candidates = []

        import re

        # Pre-process: Remove thinking/reasoning tags that some models use
        # This handles models like qwen2.5-think, deepseek-r1 that wrap reasoning in tags
        cleaned_response = re.sub(
            r"<think>.*?</think>", "", response, flags=re.DOTALL | re.IGNORECASE
        )
        cleaned_response = re.sub(
            r"<thinking>.*?</thinking>",
            "",
            cleaned_response,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Method 1: JSON in code blocks
        json_blocks = re.findall(
            r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_response, re.DOTALL
        )
        candidates.extend(json_blocks)

        # Method 2: Balanced braces
        brace_count = 0
        start_pos = -1

        for i, char in enumerate(cleaned_response):
            if char == "{":
                if brace_count == 0:
                    start_pos = i
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0 and start_pos != -1:
                    candidates.append(cleaned_response[start_pos : i + 1])

        # Method 3: Simple regex fallback
        simple_match = re.search(r"\{.*\}", cleaned_response, re.DOTALL)
        if simple_match:
            candidates.append(simple_match.group(0))

        return candidates


    def _try_parse_json(self, json_str: str) -> Optional[dict]:
        """Try to parse JSON string, return None if failed"""
        if not json_str or not json_str.strip():
            return None

        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return None


    def _basic_json_cleanup(self, json_str: str) -> str:
        """Basic cleanup for common JSON issues"""
        # Remove extra whitespace
        json_str = json_str.strip()

        # Fix common quote issues
        json_str = json_str.replace('"', '"').replace('"', '"')  # Smart quotes
        json_str = json_str.replace(""", "'").replace(""", "'")  # Smart apostrophes

        # Fix trailing commas (simple case)
        json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)

        return json_str


    def _progressive_quote_fix(self, json_str: str) -> str:
        """Progressive fixing of quote and escape issues"""
        # Only escape unescaped backslashes before quotes
        json_str = re.sub(r'(?<!\\)\\(?=")', r"\\\\", json_str)

        # Fix unescaped backslashes in string values (more conservative)
        def fix_string_content(match):
            content = match.group(1)
            # Only escape obvious problematic patterns
            content = re.sub(r"\\(?=[a-zA-Z])", r"\\\\", content)  # \alpha -> \\alpha
            return f'"{content}"'

        json_str = re.sub(r'"([^"]*(?:\\.[^"]*)*)"', fix_string_content, json_str)
        return json_str


    def _extract_fields_with_regex(self, response: str) -> dict:
        """Extract required fields using regex as last resort"""
        logger.warning("Using regex fallback for JSON parsing")

        # Extract detailed_description
        desc_match = re.search(
            r'"detailed_description":\s*"([^"]*(?:\\.[^"]*)*)"', response, re.DOTALL
        )
        description = desc_match.group(1) if desc_match else ""

        # Extract entity_name
        name_match = re.search(r'"entity_name":\s*"([^"]*(?:\\.[^"]*)*)"', response)
        entity_name = name_match.group(1) if name_match else "unknown_entity"

        # Extract entity_type
        type_match = re.search(r'"entity_type":\s*"([^"]*(?:\\.[^"]*)*)"', response)
        entity_type = type_match.group(1) if type_match else "unknown"

        # Extract summary
        summary_match = re.search(
            r'"summary":\s*"([^"]*(?:\\.[^"]*)*)"', response, re.DOTALL
        )
        summary = summary_match.group(1) if summary_match else description[:100]

        return {
            "detailed_description": description,
            "entity_info": {
                "entity_name": entity_name,
                "entity_type": entity_type,
                "summary": summary,
            },
        }


    def _extract_json_from_response(self, response: str) -> Optional[str]:
        """Legacy method - now handled by _extract_all_json_candidates"""
        candidates = self._extract_all_json_candidates(response)
        return candidates[0] if candidates else None


    def _fix_json_escapes(self, json_str: str) -> str:
        """Legacy method - now handled by progressive strategies"""
        return self._progressive_quote_fix(json_str)
