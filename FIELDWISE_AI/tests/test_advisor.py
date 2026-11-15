"""Phase 5 tests: advisor grounding and fallback (no network used)."""

import os
import unittest
from types import SimpleNamespace
from unittest import mock

from modules import advisor
from modules.kyro_service import build_plan


def _plan():
    return build_plan({"district": "Dharwad", "soil_type": "sandy-loam", "water_availability": "rainfed"})


def _client(text=None, error=None):
    def create(**kwargs):
        if error:
            raise error
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
    return lambda: SimpleNamespace(messages=SimpleNamespace(create=create))


class TemplateTests(unittest.TestCase):
    def test_template_mentions_limits_and_district(self):
        text = advisor.template_explanation(_plan())
        self.assertIn("Dharwad", text)
        self.assertIn("modelled", text)
        self.assertIn("agronomist", text)

    def test_template_flags_unverified_crops(self):
        plan = _plan()
        text = advisor.template_explanation(plan)
        if any(c.get("source_warnings") for r in plan["rotations"] for c in r["crop_sequence"]):
            self.assertIn("needs verification", text)


class GroundingTests(unittest.TestCase):
    def test_grounded_numbers_pass(self):
        facts = advisor.build_facts(_plan())
        top = facts["rotations"][0]["score"]
        self.assertTrue(advisor.numbers_are_grounded(f"Score is {top}.", facts))

    def test_invented_number_rejected(self):
        facts = advisor.build_facts(_plan())
        self.assertFalse(advisor.numbers_are_grounded("You will gain 37 percent more yield.", facts))


class AiExplanationTests(unittest.TestCase):
    def test_no_key_uses_template(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = advisor.ai_explanation(_plan())
        self.assertEqual(r["source"], "template")
        self.assertIn("ANTHROPIC_API_KEY", r["fallback_reason"])

    def test_good_reply_used(self):
        r = advisor.ai_explanation(_plan(), client_factory=_client("Dharwad suits these crops. Check with an agronomist."))
        self.assertEqual(r["source"], "ai")

    def test_hallucinated_numbers_fall_back(self):
        r = advisor.ai_explanation(_plan(), client_factory=_client("This raises yield by 41 percent."))
        self.assertEqual(r["source"], "template")
        self.assertIn("figures", r["fallback_reason"])

    def test_api_error_falls_back(self):
        r = advisor.ai_explanation(_plan(), client_factory=_client(error=RuntimeError("boom")))
        self.assertEqual(r["source"], "template")
        self.assertIn("RuntimeError", r["fallback_reason"])

    def test_empty_reply_falls_back(self):
        r = advisor.ai_explanation(_plan(), client_factory=_client(""))
        self.assertEqual(r["source"], "template")

    def test_key_never_in_output(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-secret"}):
            r = advisor.ai_explanation(_plan(), client_factory=_client(error=RuntimeError("x")))
        self.assertNotIn("sk-test-secret", str(r))


if __name__ == "__main__":
    unittest.main()
