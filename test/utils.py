import sys
import os
import asyncio
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from raganything import ProcessorMixin
from raganything import RAGAnythingConfig
from logging import Logger
from lightrag import LightRAG
from raganything import ImageModalProcessor, TableModalProcessor, EquationModalProcessor, GenericModalProcessor
from raganything import ContextExtractor, ContextConfig

# preparation for ligrag instance
def get_llm_model_func(api_key: str, base_url: str, llm_model: str = "gpt-4o-mini"):
    return (
        lambda prompt,
        system_prompt=None,
        history_messages=[],
        **kwargs: openai_complete_if_cache(
            llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
    )
    

def get_vision_model_func(api_key: str, base_url: str, vlm_model: str = "gpt-4o"):
    return (
        lambda prompt,
        system_prompt=None,
        history_messages=[],
        image_data=None,
        **kwargs: openai_complete_if_cache(
            vlm_model,
            "",
            system_prompt=None,
            history_messages=[],
            messages=[
                {"role": "system", "content": system_prompt} if system_prompt else None,
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            },
                        },
                    ],
                }
                if image_data
                else {"role": "user", "content": prompt},
            ],
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
        if image_data
        else openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
    )


async def initialize_rag(api_key, base_url):
    # Use environment variables for embedding configuration
    import os
    from dotenv import load_dotenv
    load_dotenv('../.env')
    
    embedding_dim = int(os.getenv("EMBEDDING_DIM", "None"))
    embedding_model = os.getenv("EMBEDDING_MODEL", "None")
    llm_model = os.getenv("LLM_MODEL", "None")
    working_dir = os.getenv("WORKING_DIR", "None")

    print("embedding_dim:", embedding_dim)
    print("embedding_model:", embedding_model)
    print("llm_model:", llm_model)
    print("working_dir:", working_dir)
    
    rag = LightRAG(
        working_dir=working_dir,
        embedding_func=EmbeddingFunc(
            embedding_dim=embedding_dim,
            max_token_size=8192,
            func=lambda texts: openai_embed(
                texts,
                model=embedding_model,
                api_key=api_key,
                base_url=base_url,
            ),
        ),
        llm_model_func=lambda prompt,
        system_prompt=None,
        history_messages=[],
        **kwargs: openai_complete_if_cache(
            llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        ),
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()

    return rag


import requests

# 测试 API 连接
def test_openai_connection(api_key, base_url):
    try:
        # 测试基础连接
        response = requests.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        print(f"Connection test status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Successfully connected to OpenAI API")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
