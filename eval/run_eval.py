"""RAG 检索评测：衡量「问对问题能否命中对的文档」。

用法（在项目根目录执行，或直接运行本文件，脚本会自行切到根目录）：
    python eval/run_eval.py                  # 用生产配置 k=3
    python eval/run_eval.py --k 10           # 指定召回数量
    python eval/run_eval.py --rerank         # 扩大召回后 LLM 重排再测
    python eval/run_eval.py --json out.json  # 保存明细，便于前后对比

指标：
    Hit@k     top-k 中是否出现期望文档（本文档集每题只有 1 个期望文档）
    Recall@k  期望文档被召回的比例
    MRR       第一个正确结果的倒数排名，越接近 1 越好（正确结果排第 1 即 1.0）
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

CASES_PATH = ROOT / "eval" / "cases.json"


def _source_name(doc) -> str:
    return os.path.basename(doc.metadata.get("source", ""))


def evaluate(k: int, use_rerank: bool, recall_k: int, top_n: int) -> dict:
    from rag.rag_service import get_rag_service

    svc = get_rag_service()
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    rows = []
    for case in cases:
        if use_rerank:
            docs = svc.retrieve_with_rerank(case["query"], recall_k=recall_k, top_n=top_n)
        else:
            docs = svc.retriever_docs(case["query"], k=k)

        names = [_source_name(d) for d in docs]
        expect = set(case["expect"])
        hit = bool(expect & set(names))
        recall = len(expect & set(names)) / len(expect) if expect else 0.0
        rr = 0.0
        for idx, name in enumerate(names, 1):
            if name in expect:
                rr = 1.0 / idx
                break

        rows.append({
            "id": case["id"],
            "query": case["query"],
            "expect": sorted(expect),
            "got": names,
            "hit": hit,
            "recall": round(recall, 4),
            "rr": round(rr, 4),
            "note": case.get("note", ""),
        })

    total = len(rows)
    summary = {
        "k": top_n if use_rerank else k,
        "mode": "vector+rerank" if use_rerank else "vector",
        "cases": total,
        "hit_rate": round(sum(r["hit"] for r in rows) / total, 4) if total else 0.0,
        "recall": round(sum(r["recall"] for r in rows) / total, 4) if total else 0.0,
        "mrr": round(sum(r["rr"] for r in rows) / total, 4) if total else 0.0,
    }
    return {"summary": summary, "rows": rows}


def print_report(result: dict) -> None:
    s = result["summary"]
    print(f"\n模式：{s['mode']}  k={s['k']}  用例数={s['cases']}")
    print("-" * 100)
    for r in result["rows"]:
        mark = "PASS" if r["hit"] else "MISS"
        top = " | ".join(r["got"][:2]) if r["got"] else "（无结果）"
        print(f"{mark}  {r['id']:<14} RR={r['rr']:.2f}  {r['query'][:20]:<22} -> {top[:48]}")
        if not r["hit"]:
            print(f"{'':6}期望：{r['expect']}  实际：{r['got']}")
    print("-" * 100)
    print(f"Hit@{s['k']}: {s['hit_rate']*100:.1f}%   Recall@{s['k']}: {s['recall']*100:.1f}%   MRR: {s['mrr']:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=3, help="纯向量模式的召回数量")
    parser.add_argument("--rerank", action="store_true", help="启用扩大召回 + LLM 重排")
    parser.add_argument("--recall-k", type=int, default=8, help="重排前的召回数量")
    parser.add_argument("--top-n", type=int, default=3, help="重排后保留的片段数")
    parser.add_argument("--json", type=str, default="", help="把明细保存为 JSON")
    args = parser.parse_args()

    res = evaluate(args.k, args.rerank, args.recall_k, args.top_n)
    print_report(res)

    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n明细已保存：{args.json}")
