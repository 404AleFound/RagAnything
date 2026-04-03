# 快速开始

## 安装文档解析器
### MinerU 安装
### Docling 安装

## 
# 工程结构
该项目整体构成如下：
```
raganything/
├── docs/
├── src/
├── test/
├── README.md
├── requirement.txt
└── .gitignore
```

## 解释文档区 `docs`
```
└── docs/
    ├── minerU文档解析.md
    ├── docling文档解析.md
    ├── 文本分块与向量化策略.md
    ├── 多模态转化与向量化策略.md
    ├── 向量数据库与知识图谱构建.md
    ├── prompt.md
    └── 查询策略.md
```

## 架构流程图

- 查询端与存储端的详细流程图：`docs/architecture_flow.md`

## 项目源码区 `src`
```
└── src/
    ├── parsers/
    |   ├── __init__.py
    |   ├── parser.py
    |   ├── mineru.py
    |   ├── docling.py
    |   └── batch_parser.py
    |
    ├── processors/
    |   ├── __init__.py
    |   ├── context_extractor.py
    |   ├── base_modal_processor.py
    |   ├── image_modal_processor.py
    |   ├── generic_modal_processor.py
    |   ├── table_modal_processor.py
    |   └── equation_modal_processor.py
    |
    ├── mixins/
    |   ├── __init__.py
    |   ├── batch_mixin.py
    |   ├── processor_mixin.py
    |   └── query_mixin.py
    |
    ├── utils/
    |   ├── __init__.py
    |   ├── config.py
    |   ├── types.py
    |   ├── prompt.py
    |   └── utils.py
    |
    ├── __init__.py
    └── raganything.py
```

## 测试案例区
```
└── test/
    └── samples
```

# 项目概括
- 设计并实现端到端 RAG 流水线（解析 → 切片 → embedding → 向量索引 → 检索 → 生成），支持 PDF/OCR、表格与图像的多模态解析与处理。
- 构建模块化 ModalProcessor 插件架构，实现图像/表格/文本等类型感知的批量处理与逐项回退策略，兼顾吞吐与容错。
- 实现 type-aware 批量处理与并发调度（asyncio + semaphore），通过批量描述生成与批量 embedding/upsert 显著降低 I/O 与模型调用开销。
- 与 LightRAG 集成：把文本 chunk、实体与关系批量写入向量库与知识图（支持 chunks_vdb、entities_vdb、parse_cache 等存储后端）。
- 设计健壮的上下文截断与 tokenizer-aware 逻辑，保证按 token 限制截断且尽量在句子边界结束，提升生成质量。
- 增加容错与可观测性机制：解析/多模态处理单项隔离、解析缓存、详细日志、doc_status 管理与 index_done 回调。
- 编写可测试的处理逻辑（doctest/unit-test 友好示例），并实现环境感知的启动与依赖注入（.env / sys.path / logger 注入等）。
- 化工程实践：将关键流程拆分为可复用函数、支持批量与单项两种策略、并提供回退与重试机制以提升稳定性和可维护性。
