
import json
import os
import urllib.error
import urllib.request


SYSTEM_PROMPT = """
You are a retrieval-grounded question answering controller.

You must respond with exactly one JSON object.

Available actions:

1. Search:
{"action": "search", "query": "search query"}

2. Answer:
{"action": "answer", "answer": "answer [chunk-id]", "citations": ["chunk-id"]}

Rules:
- Always search before answering.
- Use only evidence supplied in the search context.
- Never invent facts, sources, or chunk IDs.
- Cite every factual claim using [chunk-id].
- Citations must match context_ids exactly.
- If evidence is insufficient, search again using a different query.
- If evidence remains insufficient, return an answer action with
  an empty answer and empty citations so the agent abstains.
- Never use benchmark gold answers.
- Return valid JSON only, without Markdown fences.
"""


class LLMController:
    def __init__(self, model=None, base_url=None):
        self.model = model or os.getenv(
            "OPENROUTER_MODEL", "cx/gpt-6-luna"
        )
        self.base_url = (
            base_url
            or os.getenv(
                "OPENROUTER_URL",
                "https://openrouter.ai/api/v1",
            )
        ).rstrip("/")

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY chưa được cấu hình"
            )

    def decide(self, question, history):
        if not history:
            return {
                "action": "search",
                "query": question,
            }

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "search_history": history,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")

        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=90
            ) as response:
                result = json.load(response)

        except urllib.error.HTTPError as exc:
            details = exc.read().decode(
                "utf-8", errors="replace"
            )
            raise RuntimeError(
                f"LLM HTTP {exc.code}: {details[:500]}"
            ) from exc

        content = result["choices"][0]["message"]["content"]

        if not isinstance(content, str):
            raise ValueError("LLM response content không hợp lệ")

        # DEBUG: Kiểm tra phản hồi thực tế từ LLM
        print("\n========== LLM RAW RESPONSE ==========")
        print(content)
        print("======================================\n")

        # DEBUG: Kiểm tra các chunk ID được phép trích dẫn
        if history:
            print("VALID CONTEXT IDS:")
            print(history[-1].get("context_ids", []))

        action = json.loads(content)

        # Ngăn Agent lặp lại truy vấn đã thực hiện
        if action["action"] == "search":
            new_query = action.get("query", "").strip().lower()

            previous_queries = {
                query.strip().lower()
                for item in history
                for query in item.get("queries", [])
                if isinstance(query, str)
            }

            if new_query in previous_queries:
                return {
                    "action": "answer",
                    "answer": "",
                    "citations": [],
                }
        if not isinstance(action, dict):
            raise ValueError("LLM phải trả về JSON object")


        if action.get("action") not in {"search", "answer"}:
            raise ValueError("LLM trả về action không hợp lệ")

        # Đảm bảo citation xuất hiện trong câu trả lời
        if action["action"] == "answer":
            answer = action.get("answer", "")
            citations = action.get("citations", [])

            if isinstance(answer, str) and isinstance(citations, list):
                valid_ids = {
                    str(chunk_id)
                    for item in history
                    for chunk_id in item.get("context_ids", [])
                }

                # Chỉ sử dụng các citation ID hợp lệ
                citations = [
                    cid for cid in citations
                    if isinstance(cid, str) and cid in valid_ids
                ]

                if answer.strip() and citations:
                    for cid in citations:
                        marker = f"[{cid}]"
                        if marker not in answer:
                            answer += f" {marker}"

                    action["answer"] = answer
                    action["citations"] = citations

        return action