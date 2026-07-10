"""Azure AI Search 하이브리드 쿼리 구성을 검증합니다."""

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class SearchClientStub:
    """검색 호출 인자를 기록하고 빈 결과를 반환합니다."""

    def __init__(self) -> None:
        self.search_kwargs: dict[str, object] | None = None

    def search(self, **kwargs):
        """검색 인자를 저장합니다."""
        self.search_kwargs = kwargs
        return []


class RagRetrievalTests(unittest.TestCase):
    """현재 Azure Search SDK에 맞는 벡터 쿼리를 검사합니다."""

    def test_retrieve_uses_current_vector_query_parameter(self) -> None:
        """벡터 후보 수는 k_nearest_neighbors로 전달해야 합니다."""
        module = importlib.import_module("06_rag_agent")
        search_client = SearchClientStub()

        result = module.retrieve(
            search_client,
            lambda _: [[0.1, 0.2, 0.3]],
            "요금제 질문",
            top_k=2,
        )

        self.assertEqual(result, [])
        search_kwargs = search_client.search_kwargs
        self.assertIsNotNone(search_kwargs)
        assert search_kwargs is not None
        vector_query = search_kwargs["vector_queries"][0]
        self.assertEqual(vector_query.k_nearest_neighbors, 5)
        self.assertEqual(vector_query.fields, "content_vector")
        self.assertEqual(search_kwargs["top"], 2)


if __name__ == "__main__":
    unittest.main()
