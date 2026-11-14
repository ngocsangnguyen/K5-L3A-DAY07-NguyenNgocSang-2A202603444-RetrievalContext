
import re


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def find_overlap(left, right, min_chars=25):
    a = normalize(left)
    b = normalize(right)

    for size in range(min(len(a), len(b)), min_chars - 1, -1):
        if a[-size:] == b[:size]:
            return size

    return 0


def expanded_context(results, all_chunks, budget=800):
    blocks = []
    ids = []
    seen = set()

    for hit in results:
        if hit["id"] in seen:
            continue

        neighbors = [
            c for c in all_chunks
            if c["source_id"] == hit["source_id"]
            and c["page"] == hit["page"]
            and c["id"] != hit["id"]
        ]

        best = None
        overlap = 0
        direction = None

        for neighbor in neighbors:
            before = find_overlap(neighbor["text"], hit["text"])
            after = find_overlap(hit["text"], neighbor["text"])

            if before > overlap:
                best = neighbor
                overlap = before
                direction = "before"

            if after > overlap:
                best = neighbor
                overlap = after
                direction = "after"

        if best:
            if direction == "before":
                left = normalize(best["text"])
                right = normalize(hit["text"])
                left_id = best["id"]
                right_id = hit["id"]
            else:
                left = normalize(hit["text"])
                right = normalize(best["text"])
                left_id = hit["id"]
                right_id = best["id"]

            # Lấy cửa sổ quanh vùng nối
            left_part = left[max(0, len(left) - overlap - 250):]
            right_part = right[overlap:overlap + 250]

            block = (
                f"[{left_id}] [{right_id}] "
                f"| {hit['source']} | page {hit['page']}\n"
                f"{left_part}{right_part}"
            )

            block_ids = [left_id, right_id]
        else:
            block = (
                f"[{hit['id']} | {hit['source']} | page {hit['page']}]\n"
                f"{hit['text']}"
            )
            block_ids = [hit["id"]]

        proposed = "\n\n".join(blocks + [block])

        if len(proposed) <= budget:
            blocks.append(block)
            ids.extend(block_ids)
            seen.update(block_ids)

    return "\n\n".join(blocks), list(dict.fromkeys(ids))
