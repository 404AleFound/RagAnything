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


