# 架构流程图（查询端 & 存储端）

本文件包含 RagAnything 项目中 **查询端（Query）** 与 **存储端（Ingest/Insert/Storage）** 的详细流程图（Mermaid）。

> 说明：`RAGAnything` 负责编排，核心检索、embedding、实体抽取与 merge 等由外部依赖 `lightrag` 提供；图中会以外部模块形式标注其输入输出与在本项目中的调用位置。

---

## 1) 查询端（Query Side）

### 1.1 纯文本查询：`rag.aquery(query, mode="hybrid")`

```mermaid
flowchart TD
  %% ========== Entry ==========
  A0["用户调用\nRAGAnything.aquery(query, mode)"] --> A1["QueryMixin 入口\n(raganything/mixin_query.py)"]
  A1 --> A2{"确保 LightRAG 已初始化?\n_ensure_lightrag_initialized()"}
  A2 -- 否 --> A3["初始化 LightRAG + storages\nembedding_func/llm_model_func 等注入"]
  A2 -- 是 --> A4["进入检索流程"]

  %% ========== Retrieval ==========
  A3 --> A4
  A4 --> B0{mode ?}
  B0 -- naive --> B1["纯向量检索 / 简化链路\n(LightRAG 内部)"]
  B0 -- local/hybrid/mix --> B2["混合检索链路\n(LightRAG 内部)"]

  %% ========== Hybrid (typical) ==========
  B2 --> C1["Query 预处理\n清洗/分词/可能的 query expansion"]
  C1 --> C2["Embedding(query)\n调用 embedding_func"]
  C2 --> C3["向量库检索 chunks_vdb\n(topK)"]
  C3 --> C4["候选 chunk 取回内容\ntext_chunks_db.get_by_id / 批量读取"]
  C4 --> C5["结构化存储检索（可选）\nentities_vdb / relationships_vdb / KG"]
  C5 --> C6["融合与重排（可选）\n时间/分数/去重/聚合"]
  C6 --> C7["构造上下文 Prompt\nsystem + user + retrieved context"]
  C7 --> C8["LLM 生成回答\nllm_model_func"]
  C8 --> Z0[返回 answer]

  classDef ext fill:#f6f6f6,stroke:#999,stroke-dasharray: 3 3;
  class B1,B2,C1,C2,C3,C5,C6,C8 ext;
```

### 1.2 多模态增强查询：`rag.aquery_with_multimodal(query, multimodal_content=[...])`

```mermaid
flowchart TD
  Q0["用户调用\naquery_with_multimodal(query, multimodal_content)"] --> Q1["QueryMixin 入口"]
  Q1 --> Q2{确保 LightRAG 已初始化?}
  Q2 -- 否 --> Q3[初始化 LightRAG + storages]
  Q2 -- 是 --> Q4[整理 multimodal_content]

  Q3 --> Q4
  Q4 --> Q5["将 multimodal_content 规范化\ntype=table/equation/image/text..."]
  Q5 --> Q6{"是否需要 VLM/视觉模型?"}
  Q6 -- image/需要视觉理解 --> Q7["vision_model_func\n将图片/表格等转为可读文本描述"]
  Q6 -- 否 --> Q8["跳过视觉理解"]
  Q7 --> Q9["得到\"多模态描述文本\"\n作为附加上下文"]
  Q8 --> Q9

  Q9 --> Q10[拼接：query + 多模态描述 + 检索提示词]
  Q10 --> Q11["进入 LightRAG 检索链路\n(类似 aquery 的 hybrid 检索)"]
  Q11 --> Q12[LLM 生成回答]
  Q12 --> Q13[返回 answer]

  classDef ext fill:#f6f6f6,stroke:#999,stroke-dasharray: 3 3;
  class Q7,Q11,Q12 ext;
```

---

## 2) 存储端（Storage / Ingest Side）

### 2.1 批处理主入口：`process_documents_with_rag_batch(...)`

```mermaid
flowchart TD
  S0["用户调用\nprocess_documents_with_rag_batch(file_paths,...)"] --> S1["BatchMixin 入口\n(raganything/mixin_batch.py)"]
  S1 --> S2["Stage-0: 批量解析(纯解析)\nprocess_documents_batch -> BatchParser"]
  S2 --> S3["得到 parse_result\nsuccessful_files / failed_files + 结构化内容"]
  S3 --> S4{ensure LightRAG?}
  S4 -- 否 --> S5["_ensure_lightrag_initialized\n初始化 storages + embedding/llm 注入"]
  S4 -- 是 --> S6[准备入库]

  S5 --> S6
  S6 --> S7["遍历 successful_files"]
  S7 --> S8["对每个文件调用\nprocess_document_complete(file_path,...)"]
  S8 --> S9["写入 doc_status / track_id / 去重检测"]
  S9 --> S7
  S7 --> S10[完成：输出汇总/记录失败项]
```

### 2.2 单文件完整入库：`process_document_complete(file_path, ...)`

```mermaid
flowchart TD
  D0["process_document_complete(file_path,...)"] --> D1["ProcessorMixin 入口\n(raganything/mixin_processor.py)"]

  %% Parse
  D1 --> D2["parse_document(file_path)\nparser=mineru/docling/..."]
  D2 --> D3{"命中 parse_cache?"}
  D3 -- 是 --> D4["读取缓存的 parse 结果"]
  D3 -- 否 --> D5["调用 parser 实际解析\n可能含 OCR / layout / 结构化输出"]
  D5 --> D6[写入 parse_cache]
  D4 --> D7[得到统一结构化 content<br/>text + multimodal items]
  D6 --> D7

  %% Text insert
  D7 --> D8["Stage-1: 文本内容入库\nLightRAG.insert_text / text_chunks 写入"]
  D8 --> D9["text_chunks_db.upsert\nchunks_vdb.upsert(触发 embedding)"]

  %% Multimodal insert (intra-doc concurrency)
  D7 --> D10["Stage-2: 多模态内容处理\n_process_multimodal_content_batch_type_aware"]
  D10 --> D11["按 type 分发 Processor\nImage/Table/Equation/Generic..."]
  D11 --> D12["并发处理 items (Semaphore)\ncreate_task + gather"]
  D12 --> D13["每个 item 生成 modal_chunk + entity_info"]
  D13 --> D14[BaseModalProcessor._create_entity_and_chunk]
  D14 --> D15["text_chunks_db.upsert(模态 chunk)"]
  D15 --> D16["chunks_vdb.upsert(模态 chunk 向量化)"]
  D16 --> D17["KG: upsert_node(entity)"]
  D17 --> D18["entities_vdb.upsert(entity 向量化)"]
  D18 --> D19["_process_chunk_for_extraction -> extract_entities"]
  D19 --> D20["relationships_vdb.upsert(关系向量)"]
  D20 --> D21["merge_nodes_and_edges\n合并到 KG + VDB"]
  D21 --> D22["lightrag._insert_done() flush/commit"]

  %% Final
  D22 --> D23["更新 doc_status: SUCCESS/FAILED + chunks_list"]
  D23 --> D24["返回结果"]

  classDef ext fill:#f6f6f6,stroke:#999,stroke-dasharray: 3 3;
  class D8,D9,D19,D21,D22 ext;
```

---

## 3) 总览：查询端 vs 存储端共享同一套存储

```mermaid
flowchart LR
  subgraph Ingest[存储端 / 入库端]
    I1[process_documents_with_rag_batch<br/>/ process_folder_complete] --> I2[process_document_complete]
    I2 --> I3[text chunks 入库]
    I2 --> I4[multimodal chunks 入库]
    I4 --> I5[extract_entities + merge]
  end

  subgraph Storages[LightRAG Storages]
    K1[text_chunks_db (KV)]
    V1[chunks_vdb (Vector)]
    V2[entities_vdb (Vector)]
    V3[relationships_vdb (Vector)]
    G1[chunk_entity_relation_graph (KG)]
    S1[doc_status / parse_cache / llm cache]
  end

  subgraph Query[查询端 / 检索端]
    Q1[aquery / aquery_with_multimodal] --> Q2[LightRAG 检索 + 重排]
    Q2 --> Q3[LLM 生成回答]
  end

  I3 --> K1
  I3 --> V1
  I4 --> K1
  I4 --> V1
  I5 --> V2
  I5 --> V3
  I5 --> G1
  I2 --> S1

  Q2 --> K1
  Q2 --> V1
  Q2 --> V2
  Q2 --> V3
  Q2 --> G1
  Q2 --> S1
```
