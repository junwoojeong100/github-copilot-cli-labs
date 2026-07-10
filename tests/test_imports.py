"""모든 예제 모듈이 네트워크 호출 없이 임포트되는지 검증합니다."""

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class ExampleImportTests(unittest.TestCase):
    """예제와 공통 헬퍼의 임포트 회귀를 검사합니다."""

    def test_all_example_modules_import(self) -> None:
        """모든 모듈의 SDK 임포트 경로가 유효해야 합니다."""
        modules = [
            "01_single_agent",
            "02_sequential_workflow",
            "03_group_chat",
            "04_concurrent_workflow",
            "05_mcp_agent",
            "06_rag_agent",
            "06_rag_agent_foundry_iq",
            "_indexing",
            "_rag_iq",
            "_streaming",
        ]

        for module in modules:
            with self.subTest(module=module):
                importlib.import_module(module)


if __name__ == "__main__":
    unittest.main()
