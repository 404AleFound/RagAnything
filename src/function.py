import base64
import asyncio
from typing import Any, Dict, Optional, Tuple
from lightrag import LightRAG
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.openai import openai_complete_if_cache, openai_embed


def get_llm_model_func(api_key: str, base_url: Optional[str] = None):
    """
    ---
    Note:
    ---
    Get the LLM model function with the specified API key and base URL.
    
    """
    return (
        lambda prompt,
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
    
    
def get_vision_model_func(api_key: str, base_url: Optional[str] = None):
    return (
        lambda prompt,
        system_prompt=None,
        history_messages=[],
        image_data=None,
        **kwargs: openai_complete_if_cache(
            "gpt-4o",
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


async def run_llm(api_key, base_url):
    llm_func = get_llm_model_func(api_key, base_url)
    response = await llm_func("Hello, world!", system_prompt="You are a helpful assistant.")
    print(response)
    
async def run_vision(api_key, base_url):
    vision_func = get_vision_model_func(api_key, base_url)
    image_path = "../../test/samples/imgs/01.png"
    
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")         
    response = await vision_func("What do you see?", image_data=image_base64, system_prompt="You are a helpful assistant that describes images.")
    print(response)

def main():
    from dotenv import load_dotenv
    import os
    load_dotenv("../../.env")
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")
    # asyncio.run(run_llm(api_key, base_url))
    asyncio.run(run_vision(api_key, base_url))

if __name__ == "__main__":
    main()