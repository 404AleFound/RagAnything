import json
import base64
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
from lightrag.lightrag import LightRAG
from lightrag.utils import logger, compute_mdhash_id

from .mp_base import BaseModalProcessor
from .context_extractor import ContextExtractor
from ..prompt import PROMPTS

class ImageModalProcessor(BaseModalProcessor):
    """Processor specialized for image content"""

    def __init__(self, lightrag: LightRAG, modal_caption_func, context_extractor: Optional[ContextExtractor] = None,):
        """
        ---
        Note:
        ---
        Initialize image processor

        ---
        Args:
        ---
        lightrag: LightRAG instance
        modal_caption_func: Function for generating descriptions (supporting image understanding)
        context_extractor: Context extractor instance
        
        """
        super().__init__(lightrag, modal_caption_func, context_extractor)

    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        ---
        Note:
        ---
        Encode image to base64
        
        """
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            return ""

    async def generate_description_only(self, modal_content, content_type: str, item_info: Optional[Dict[str, Any]] = None,
                                        entity_name: Optional[str] = None,) -> Tuple[str, Dict[str, Any]]:
        """
        ---
        Note:
        ---
        Generate image description and entity info only, without entity relation extraction.
        Used for batch processing stage 1.

        ---
        Args:
        ---
        modal_content: Image content to process
        content_type: Type of modal content ("image")
        item_info: Item information for context extraction
        entity_name: Optional predefined entity name

        ---
        Returns:
        ---
        Tuple of (enhanced_caption, entity_info)
        
        """
        try:
            # Parse image content (reuse existing logic)
            if isinstance(modal_content, str):
                try:
                    content_data = json.loads(modal_content)
                except json.JSONDecodeError:
                    content_data = {"description": modal_content}
            else:
                content_data = modal_content

            image_path  = content_data.get("img_path")
            captions    = content_data.get("image_caption", content_data.get("img_caption", []))
            footnotes   = content_data.get("image_footnote", content_data.get("img_footnote", []))

            # Validate image path
            if not image_path:
                raise ValueError(f"No image path provided in modal_content: {modal_content}")

            # Convert to Path object and check if it exists
            image_path_obj = Path(image_path)
            if not image_path_obj.exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")

            # Extract context for current item
            context = ""
            if item_info:
                context = self._get_context_for_item(item_info)

            # Build detailed visual analysis prompt with context
            if context:
                vision_prompt = PROMPTS.get("vision_prompt_with_context", PROMPTS["vision_prompt"]).format(
                    context=context,
                    entity_name=entity_name
                    if entity_name
                    else "unique descriptive name for this image",
                    image_path=image_path,
                    captions=captions if captions else "None",
                    footnotes=footnotes if footnotes else "None",
                )
            else:
                vision_prompt = PROMPTS["vision_prompt"].format(
                    entity_name=entity_name
                    if entity_name
                    else "unique descriptive name for this image",
                    image_path=image_path,
                    captions=captions if captions else "None",
                    footnotes=footnotes if footnotes else "None",
                )

            # Encode image to base64
            image_base64 = self._encode_image_to_base64(image_path)
            if not image_base64:
                raise RuntimeError(f"Failed to encode image to base64: {image_path}")

            # Call vision model with encoded image
            response = await self.modal_caption_func(
                vision_prompt,
                image_data=image_base64,
                system_prompt=PROMPTS["IMAGE_ANALYSIS_SYSTEM"],
            )

            # Parse response (reuse existing logic)
            enhanced_caption, entity_info = self._parse_response(response, entity_name)

            return enhanced_caption, entity_info

        except Exception as e:
            logger.error(f"Error generating image description: {e}")
            # Fallback processing
            fallback_entity = {
                "entity_name": entity_name
                if entity_name
                else f"image_{compute_mdhash_id(str(modal_content))}",
                "entity_type": "image",
                "summary": f"Image content: {str(modal_content)[:100]}",
            }
            return str(modal_content), fallback_entity

    async def process_multimodal_content(self, modal_content, content_type: str, file_path: str = "manual_creation", 
                                         entity_name: Optional[str] = None, item_info: Optional[Dict[str, Any]] = None, batch_mode: bool = False, 
                                         doc_id: Optional[str] = None, chunk_order_index: int = 0,) -> Tuple[str, Dict[str, Any]]:
        """
        ---
        Note:
        ---
        Process image content with context support
        
        """
        try:
            # Generate description and entity info
            enhanced_caption, entity_info = await self.generate_description_only(
                modal_content, content_type, item_info, entity_name
            )

            # Build complete image content
            if isinstance(modal_content, str):
                try:
                    content_data = json.loads(modal_content)
                except json.JSONDecodeError:
                    content_data = {"description": modal_content}
            else:
                content_data = modal_content

            image_path = content_data.get("img_path", "")
            captions = content_data.get(
                "image_caption", content_data.get("img_caption", [])
            )
            footnotes = content_data.get(
                "image_footnote", content_data.get("img_footnote", [])
            )

            modal_chunk = PROMPTS["image_chunk"].format(
                image_path=image_path,
                captions=", ".join(captions) if captions else "None",
                footnotes=", ".join(footnotes) if footnotes else "None",
                enhanced_caption=enhanced_caption,
            )

            return await self._create_entity_and_chunk(
                modal_chunk,
                entity_info,
                file_path,
                batch_mode,
                doc_id,
                chunk_order_index,
            )

        except Exception as e:
            logger.error(f"Error processing image content: {e}")
            # Fallback processing
            fallback_entity = {
                "entity_name": entity_name
                if entity_name
                else f"image_{compute_mdhash_id(str(modal_content))}",
                "entity_type": "image",
                "summary": f"Image content: {str(modal_content)[:100]}",
            }
            return str(modal_content), fallback_entity

    def _parse_response(self, response: str, entity_name: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        """
        ---
        Note:
        ---
        Parse model response
        
        """
        try:
            response_data = self._robust_json_parse(response)

            description = response_data.get("detailed_description", "")
            entity_data = response_data.get("entity_info", {})

            if not description or not entity_data:
                raise ValueError("Missing required fields in response")

            if not all(key in entity_data for key in ["entity_name", "entity_type", "summary"]):
                raise ValueError("Missing required fields in entity_info")

            entity_data["entity_name"] = (
                entity_data["entity_name"] + f" ({entity_data['entity_type']})"
            )
            if entity_name:
                entity_data["entity_name"] = entity_name

            return description, entity_data

        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logger.error(f"Error parsing image analysis response: {e}")
            logger.debug(f"Raw response: {response}")
            fallback_entity = {
                "entity_name": entity_name
                if entity_name
                else f"image_{compute_mdhash_id(response)}",
                "entity_type": "image",
                "summary": response[:100] + "..." if len(response) > 100 else response,
            }
            return response, fallback_entity


async def test_init_processor():
    import os
    from lightrag.utils import EmbeddingFunc
    from lightrag.llm.openai import openai_complete_if_cache, openai_embed
    from lightrag.kg.shared_storage import initialize_pipeline_status

    WORKING_DIR = "./working_dir"
    
    embedding_dim =     int(os.getenv("EMBEDDING_DIM", "3072"))
    embedding_model =   os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    api_key =           os.getenv("EMBEDDING_BINDING_API_KEY", "")
    base_url =          os.getenv("EMBEDDING_BASE_URL", "https://openrouter.ai/api/v1")

    rag = LightRAG(working_dir=WORKING_DIR,
        embedding_func=EmbeddingFunc(
            embedding_dim=embedding_dim,
            max_token_size=8192,
            func=lambda texts: openai_embed(texts, model=embedding_model, api_key=api_key, base_url=base_url),
        ),
        llm_model_func=lambda prompt,
        system_prompt=None,
        history_messages=[],
        **kwargs: openai_complete_if_cache(
            "gpt-oss-120b",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()
    processor = ImageModalProcessor(rag, None)
    return processor

async def test_main():
    processor = await test_init_processor()

    """
    Test 1: for _encode_image_to_base64
    """
    image_path = "../../test/samples/imgs/01.png"
    image_encoded = processor._encode_image_to_base64(image_path)
    print(len(image_encoded))
    
    
    """
    Test 2: for _parse_response
    """
    response = '{"detailed_description": "A beautiful sunset over the mountains.", "entity_info": {"entity_name": "sunset", "entity_type": "image", "summary": "A stunning sunset"}}}'
    image_description, image_entity = processor._parse_response(response)
    print(image_description)
    print(image_entity)
    
    
    """
    Test 3: for generate_image_description
    """
    image_content = {
        "img_path": "../../test/samples/imgs/01.png",
        "image_caption": [
            "Example image caption"
        ],
        "image_footnote": [
            "Example image footnote"
        ]
    }
    content_type = "image"
    image_description = await processor.generate_description_only(image_content, image_encoded)
    print(image_description)


if __name__ == "__main__":
    asyncio.run(test_main())