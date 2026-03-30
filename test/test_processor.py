# Author: Ale
# Date: 20260329
# File: test_processor.py
# Brief: a test file for class ProcessorMixin

import sys
import os
import asyncio
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from lightrag.kg.shared_storage import initialize_pipeline_status

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src import ProcessorMixin
from src import RAGAnythingConfig
import logging
from lightrag import LightRAG
from src import ImageModalProcessor, TableModalProcessor, EquationModalProcessor, GenericModalProcessor
from src import ContextExtractor, ContextConfig

from utils import initialize_rag, get_llm_model_func, get_vision_model_func

TEST_PDF_PATH = "../data/pdf/output/Very_Deep_Convolutional_Networks_for_Large-Scale_Image_Recognition/hybrid_auto/Very_Deep_Convolutional_Networks_for_Large-Scale_Image_Recognition_content_list.json"


def _get_file_reference_TEST(pm : ProcessorMixin):
    test_data = TEST_PDF_PATH
    
    res = pm._get_file_reference(test_data)
    
    print("The returned of _get_file_reference_TEST is:")
    
    print(res + '\n')
    
    # expected: A_compact_algorithm_for_rectification_of_stereo_pairs.pdf
    

def _generate_cache_key_TEST(pm: ProcessorMixin):
    from pathlib import Path
    
    file_path = Path(TEST_PDF_PATH)
    
    res = pm._generate_cache_key(file_path, parse_method="ocr")
    
    print("The returned of _generate_cache_key_TEST is:")
    
    print(res + '\n')
    
    # expected: 8ee10f73a2820ae31a12b4731986bb47


def _generate_content_based_doc_id_TEST(pm: ProcessorMixin):
    import json
    
    content_file = TEST_PDF_PATH
    
    content_list = json.load(open(content_file, "r", encoding="utf-8"))
    
    res = pm._generate_content_based_doc_id(content_list)
    
    print("The returned of _generate_content_based_doc_id_test is:")
    
    print(res + '\n')
    
    # expected: doc-ca634d83aa163cccbed4def222941b3b like


def _get_cached_result_TEST(pm: ProcessorMixin):
    pass


def _store_cached_result_TEST(pm: ProcessorMixin):
    pass


async def parse_document_TEST(pm: ProcessorMixin):
    file_path = TEST_PDF_PATH
    
    res = await pm.parse_document(file_path, output_dir="./data_parsed", parse_method="auto", display_stats=True)
    
    print(res)
    # expected: <parsed_document>


async def _process_multimodal_content_TEST(pm: ProcessorMixin):
    pass


async def _process_multimodal_content_individual_TEST(pm: ProcessorMixin):
    import json
    
    content_file = TEST_PDF_PATH
    
    content_list = json.load(open(content_file, "r", encoding="utf-8"))
    
    print(content_list[0])  # Print the first item for brevity
    
    doc_id = pm._generate_content_based_doc_id(content_list)

    print(doc_id)
    
    await pm._process_multimodal_content_individual(content_list, content_file, doc_id)


async def _process_multimodal_content_batch_type_aware_TEST(pm: ProcessorMixin):
    import json
    
    content_file = TEST_PDF_PATH
    
    content_list = json.load(open(content_file, "r", encoding="utf-8"))
    
    doc_id = pm._generate_content_based_doc_id(content_list)
    
    await pm._process_multimodal_content_batch_type_aware(content_list, content_file, doc_id) 

    

async def main_test():
    """
    Initialize the ProcessorMixin instance.
    """    
    
    pm = ProcessorMixin()
    
    pm.config = RAGAnythingConfig()
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    pm.logger = logging.getLogger("ProcessorMixinTestLogger")

    import os
    from dotenv import load_dotenv
    load_dotenv('../.env')
    api_key = os.getenv("API_KEY", "")
    base_url = os.getenv("BASE_URL", "")

    pm.lightrag = await initialize_rag(api_key, base_url)
    pm.llm_model_func = get_llm_model_func(api_key, base_url)
    pm.vision_model_func = get_vision_model_func(api_key, base_url)
    pm.modal_processors = {
        "image":    ImageModalProcessor(pm.lightrag, pm.vision_model_func),
        "table":    TableModalProcessor(pm.lightrag, pm.llm_model_func),
        "equation": EquationModalProcessor(pm.lightrag, pm.llm_model_func),
        "generic":  GenericModalProcessor(pm.lightrag, pm.llm_model_func),
    }
    # pm.embedding_model_func = get_embedding_model_func(api_key, base_url)

    """
    Test 1: _get_file_reference_TEST()
    """
    # _get_file_reference_TEST(pm)

    """
    Test 2: _generate_cache_key_TEST()
    """
    # _generate_cache_key_TEST(pm)


    """
    Test 3: _generate_content_based_doc_id_TEST()
    """
    # _generate_content_based_doc_id_TEST(pm)

    
    """
    Test 4: _get_cached_result_TEST()
    """
    # _get_cached_result_TEST(pm)


    """
    Test 5: _store_cached_result_TEST()
    """
    # _store_cached_result_TEST(pm)


    """
    Test 6: parse_document_TEST()
    """
    # asyncio.run(parse_document_TEST(pm))


    """

    Test: _process_multimodal_content_individual_TEST()
    
    Details:
        time cost: 55 mins
    """
    # await _process_multimodal_content_individual_TEST(pm)
    
    
    """

    Test: _process_multimodal_content_batch_type_aware_TEST()
    
    Details:
        time cost: 20 mins
    """
    await _process_multimodal_content_batch_type_aware_TEST(pm)

if __name__ == "__main__":
    asyncio.run(main_test())
