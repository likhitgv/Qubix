"""Phase 5 tests: advisor grounding and fallback (no network used)."""

import os
import unittest
from types import SimpleNamespace
from unittest import mock

from modules import advisor
from modules.kairo_service import build_plan


def _plan():
    return build_plan({"district": "Dharwad", "soil_type": "sandy-loam", "water_availability": "rainfed"})


CFG = {"provider": "groq", "api_key": "sk-test-secret",
       "base_url": "https://example.test/v1", "model": "m"}


def _post(text=None, error=None, status_error=None):
    def post(url, headers=None, json=None, timeout=None):
        if error:
            raise error

        def raise_for_status():
            if status_error:
                raise status_error

        return SimpleNamespace(
            raise_for_status=raise_for_status,
            json=lambda: {"choices": [{"message": {"content": text}}]},
        )
    return post


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
        env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
        with mock.patch.dict(os.environ, env, clear=True):
            r = advisor.ai_explanation(_plan())
        self.assertEqual(r["source"], "template")
        self.assertIn("No AI provider key", r["fallback_reason"])

    def test_good_reply_used(self):
        r = advisor.ai_explanation(_plan(), post=_post("Dharwad suits these crops."), config=CFG)
        self.assertEqual(r["source"], "ai")

    def test_disclaimer_always_appended_to_ai_text(self):
        r = advisor.ai_explanation(_plan(), post=_post("Dharwad suits these crops."), config=CFG)
        self.assertIn("agronomist", r["text"])
        self.assertIn("modelled", r["text"])

    def test_hallucinated_numbers_fall_back(self):
        r = advisor.ai_explanation(_plan(), post=_post("This raises yield by 41 percent."), config=CFG)
        self.assertEqual(r["source"], "template")
        self.assertIn("figures", r["fallback_reason"])

    def test_network_error_falls_back(self):
        r = advisor.ai_explanation(_plan(), post=_post(error=ConnectionError("boom")), config=CFG)
        self.assertEqual(r["source"], "template")
        self.assertIn("ConnectionError", r["fallback_reason"])

    def test_http_error_falls_back(self):
        r = advisor.ai_explanation(_plan(), post=_post("x", status_error=RuntimeError("429")), config=CFG)
        self.assertEqual(r["source"], "template")

    def test_empty_reply_falls_back(self):
        r = advisor.ai_explanation(_plan(), post=_post(""), config=CFG)
        self.assertEqual(r["source"], "template")

    def test_key_never_in_output(self):
        r = advisor.ai_explanation(_plan(), post=_post(error=RuntimeError("sk-test-secret leaked")), config=CFG)
        self.assertNotIn("sk-test-secret", str(r))

    def test_request_uses_bearer_and_chat_endpoint(self):
        seen = {}

        def post(url, headers=None, json=None, timeout=None):
            seen.update(url=url, headers=headers, body=json)
            return _post("ok")(url)

        advisor.ai_explanation(_plan(), post=post, config=CFG)
        self.assertEqual(seen["url"], "https://example.test/v1/chat/completions")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer sk-test-secret")
        self.assertEqual(seen["body"]["messages"][0]["role"], "system")


class ProviderConfigTests(unittest.TestCase):
    def _env(self, **extra):
        base = {k: v for k, v in os.environ.items()
                if not k.endswith("_API_KEY") and not k.startswith(("KAIRO_", "KYRO_"))}
        base.update(extra)
        return mock.patch.dict(os.environ, base, clear=True)

    def test_default_provider_groq(self):
        with self._env(GROQ_API_KEY="k"):
            cfg = advisor.provider_config()
        self.assertEqual(cfg["provider"], "groq")
        self.assertIn("groq.com", cfg["base_url"])

    def test_switch_to_gemini(self):
        with self._env(KAIRO_AI_PROVIDER="gemini", GEMINI_API_KEY="k"):
            self.assertEqual(advisor.provider_config()["provider"], "gemini")

    def test_wrong_key_for_provider_is_unavailable(self):
        with self._env(KAIRO_AI_PROVIDER="gemini", GROQ_API_KEY="k"):
            self.assertFalse(advisor.ai_available())

    def test_unknown_provider_unavailable(self):
        with self._env(KAIRO_AI_PROVIDER="nope", GROQ_API_KEY="k"):
            self.assertFalse(advisor.ai_available())

    def test_legacy_kyro_variables_still_work(self):
        with self._env(KYRO_AI_PROVIDER="gemini", GEMINI_API_KEY="k", KYRO_MODEL="old-name"):
            cfg = advisor.provider_config()
        self.assertEqual(cfg["provider"], "gemini")
        self.assertEqual(cfg["model"], "old-name")

    def test_kairo_variable_wins_over_legacy(self):
        with self._env(KAIRO_MODEL="new", KYRO_MODEL="old", GROQ_API_KEY="k"):
            self.assertEqual(advisor.provider_config()["model"], "new")

    def test_model_override(self):
        with self._env(GROQ_API_KEY="k", KAIRO_MODEL="custom-model"):
            self.assertEqual(advisor.provider_config()["model"], "custom-model")


if __name__ == "__main__":
    unittest.main()
