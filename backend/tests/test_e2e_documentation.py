import unittest
from pathlib import Path


class E2EDocumentationTest(unittest.TestCase):
    def test_e2e_script_and_manual_guide_cover_critical_flow(self):
        root = Path(__file__).resolve().parents[2]
        guide_path = root / "docs" / "e2e-test-solis.md"
        script_path = root / "scripts" / "e2e-smoke.ps1"
        if not guide_path.exists() or not script_path.exists():
            self.skipTest("Documentacao E2E fica fora do contexto Docker do backend.")

        guide = guide_path.read_text(encoding="utf-8")
        script = script_path.read_text(encoding="utf-8")

        expected_markers = [
            "docker compose up --build",
            "Invoke-RestMethod http://localhost:8000/health",
            "Diagnostico",
            "Modo demonstracao",
            "LGPD",
            "Upload da conta",
            "Parser CPFL",
            "Aplicar ao lead",
            "Kit",
            "PDF",
            "Link seguro",
            "docker compose stop backend",
            "Tentar reconectar",
        ]
        for marker in expected_markers:
            self.assertIn(marker, guide)

        self.assertIn("docker compose up -d --build", script)
        self.assertIn("python -m unittest discover tests", script)
        self.assertIn("npm test", script)


if __name__ == "__main__":
    unittest.main()
