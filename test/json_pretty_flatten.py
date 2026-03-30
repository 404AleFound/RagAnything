# python
import json
from typing import Any, Dict, Iterable, Optional
import sys

def _iter_json_records(path: str) -> Iterable[Any]:
    """迭代文件中的 JSON 记录：支持 JSONL（每行一个 JSON）或单行 JSON array。"""
    with open(path, "r", encoding="utf-8") as f:
        # 读取首个非空白字符判断格式
        # 回到文件开头后根据格式处理（兼容大文件）
        first = f.read(1024).lstrip()
        f.seek(0)
        if not first:
            return
        if first[0] == "[":
            # 整个文件是一个 JSON 数组
            data = json.load(f)
            for item in data:
                yield item
        else:
            # 按行解析（每行一个 JSON）
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # 容错：尝试去除逗号结尾或其它小修正再解析
                    try:
                        clean = line.rstrip(",")
                        yield json.loads(clean)
                    except Exception as e:
                        print(f"Warning: failed to parse line: {e}", file=sys.stderr)


def pretty_print_jsonl(input_path: str, output_path: Optional[str] = None, indent: int = 2, ensure_ascii: bool = False) -> int:
    """
    将单行 JSON/JSONL 文件展开为带缩进的多行 JSON.

    Args:
      input_path: 源文件路径（JSONL 或 单一 JSON 数组）
      output_path: 若提供则写入该文件（覆盖），否则打印到 stdout
      indent: 缩进空格数
      ensure_ascii: 是否转义非 ASCII 字符（默认 False，保持中文可读）

    Returns:
      处理的记录数
    """
    out = open(output_path, "w", encoding="utf-8") if output_path else None
    count = 0
    try:
        for record in _iter_json_records(input_path):
            formatted = json.dumps(record, ensure_ascii=ensure_ascii, indent=indent, separators=(",", ": "))
            if out:
                out.write(formatted)
                out.write("\n")  # 用空行分隔每个对象
            else:
                print(formatted)
            count += 1
    finally:
        if out:
            out.close()
    return count


def _flatten(obj: Any, parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """递归扁平化 dict/list，列表以索引形式加入 key（如 a.0.b）。"""
    items: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.update(_flatten(v, new_key, sep=sep))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.update(_flatten(v, new_key, sep=sep))
    else:
        items[parent_key] = obj
    return items


def flatten_jsonl(input_path: str, output_path: Optional[str] = None, sep: str = ".") -> int:
    """
    将每个 JSON 记录扁平化后以单行 JSON 输出（每行一个扁平化对象）。

    Args:
      input_path: 源文件路径
      output_path: 输出路径（若 None 打印到 stdout）
      sep: 扁平化键的分隔符

    Returns:
      处理记录数
    """
    out = open(output_path, "w", encoding="utf-8") if output_path else None
    count = 0
    try:
        for record in _iter_json_records(input_path):
            flat = _flatten(record, parent_key="", sep=sep)
            line = json.dumps(flat, ensure_ascii=False)
            if out:
                out.write(line + "\n")
            else:
                print(line)
            count += 1
    finally:
        if out:
            out.close()
    return count


# 简单使用示例（在脚本/REPL 中调用）
# pretty_print_jsonl("./test/raganything_working_dir/vdb_chunks.json", "./test/raganything_working_dir/vdb_chunks_pretty.json")
# pretty_print_jsonl("./test/raganything_working_dir/vdb_relationships.json", "./test/raganything_working_dir/vdb_relationships_pretty.json")
# pretty_print_jsonl("./test/raganything_working_dir/vdb_entities.json", "./test/raganything_working_dir/vdb_entities_pretty.json")
# flatten_jsonl("./test/raganything_working_dir/vdb_chunks.json", "vdb_chunks_flat.json")