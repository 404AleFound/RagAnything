__name__ = "raganything"

# use explicit relative imports so package imports work when `src` is imported
from .parsers import BatchParser, BatchProcessingResult
from .parsers import DoclingParser
from .parsers import MineruParser

from .processors.context_extractor import ContextExtractor
from .processors.mp_base import BaseModalProcessor
from .processors.mp_image import ImageModalProcessor
from .processors.mp_table import TableModalProcessor
from .processors.mp_equation import EquationModalProcessor
from .processors.mp_generic import GenericModalProcessor
from .processors.context_extractor import ContextExtractor, ContextConfig

from .batch import BatchMixin
from .processor import ProcessorMixin
from .query import QueryMixin
from .config import RAGAnythingConfig