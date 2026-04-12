"""
Unit Tests - Emotion Modules (Phase 2-4)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.emotion.occ_model import EmotionSynthesizer, EmotionCategory, EmotionState
from src.emotion.emotion_synthesis import (
    EmotionAwareResponseGenerator, DualEmotionEncoding,
    AffinityDecoder, EmotionConsistencyChecker, ProsodySettings
)
from src.emotion.pad_model import PADVector, PADSpace, EMOTION_PAD_MAP
from src.emotion.multimodal_recognizer import (
    MultimodalEmotionRecognizer, SpeechProsodyAnalyzer,
    TextSentimentAnalyzer, FacialExpressionAnalyzer
)
from src.emotion.epitome_framework import (
    EPITOMEFramework, EPITOMEContext,
    EmotionalReactionPhase, InterpretationPhase, ExplorationPhase
)
from src.emotion.metacognitive_layer import (
    MetacognitiveLayer, ResponseQualityEvaluator,
    ErrorDetector, EmotionalAppropriatenessChecker, SelfReflectionEngine
)


# ---------------------------------------------------------------------------
# OCC Appraisal Model
# ---------------------------------------------------------------------------

class TestEmotionSynthesizer(unittest.TestCase):
    def setUp(self):
        self.synth = EmotionSynthesizer()

    def test_appraise_positive_likely(self):
        result = self.synth.appraise(desirability=0.8, likelihood=0.9, expectedness=0.5)
        self.assertIsInstance(result.emotion, EmotionCategory)
        self.assertGreater(result.intensity, 0)

    def test_appraise_negative_likely(self):
        result = self.synth.appraise(desirability=-0.8, likelihood=0.9, expectedness=0.5)
        self.assertIn(result.emotion, (
            EmotionCategory.DISTRESS, EmotionCategory.FEARS_CONFIRMED
        ))

    def test_appraise_clamps_values(self):
        result = self.synth.appraise(desirability=5.0, likelihood=5.0, expectedness=5.0)
        self.assertLessEqual(result.desirability, 1.0)
        self.assertLessEqual(result.likelihood, 1.0)

    def test_emotion_taxonomy_structure(self):
        taxonomy = self.synth.get_emotion_taxonomy()
        self.assertIn("event_reactions", taxonomy)
        self.assertIn("agent_reactions", taxonomy)
        self.assertIn("object_reactions", taxonomy)
        self.assertIn("compound", taxonomy)

    def test_state_updates_when_enabled(self):
        self.synth.enable()
        self.synth.appraise(0.9, 0.9, 0.5)
        self.assertIsNotNone(self.synth.state.dominant)

    def test_state_not_updated_when_disabled(self):
        self.synth.disable()
        self.synth.appraise(0.9, 0.9, 0.5)
        self.assertIsNone(self.synth.state.dominant)

    def test_reset_state(self):
        self.synth.enable()
        self.synth.appraise(0.9, 0.9, 0.5)
        self.synth.reset_state()
        self.assertIsNone(self.synth.state.dominant)


# ---------------------------------------------------------------------------
# Emotion Synthesis
# ---------------------------------------------------------------------------

class TestAffinityDecoder(unittest.TestCase):
    def test_positive_text(self):
        decoder = AffinityDecoder()
        valence, arousal = decoder.decode("I am so happy and wonderful today")
        self.assertGreater(valence, 0)

    def test_negative_text(self):
        decoder = AffinityDecoder()
        valence, arousal = decoder.decode("I feel terrible and awful")
        self.assertLess(valence, 0)

    def test_neutral_text(self):
        decoder = AffinityDecoder()
        valence, arousal = decoder.decode("The weather is cloudy")
        self.assertAlmostEqual(valence, 0.0, places=1)


class TestEmotionConsistencyChecker(unittest.TestCase):
    def test_consistent_positive(self):
        checker = EmotionConsistencyChecker()
        result = checker.check("That's great news!", EmotionCategory.JOY)
        self.assertTrue(result)

    def test_inconsistent_positive_emotion_negative_text(self):
        checker = EmotionConsistencyChecker()
        result = checker.check("I'm sorry to hear that", EmotionCategory.JOY)
        self.assertFalse(result)

    def test_none_emotion_always_consistent(self):
        checker = EmotionConsistencyChecker()
        self.assertTrue(checker.check("anything", None))


class TestEmotionAwareResponseGenerator(unittest.TestCase):
    def setUp(self):
        self.gen = EmotionAwareResponseGenerator()
        self.gen.enable()

    def test_generates_response_with_emotion(self):
        response, prosody = self.gen.generate("It worked!", EmotionCategory.JOY)
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_prosody_settings_for_joy(self):
        _, prosody = self.gen.generate("content", EmotionCategory.JOY)
        self.assertIsInstance(prosody, ProsodySettings)
        self.assertGreater(prosody.rate, 1.0)

    def test_disabled_returns_plain_content(self):
        self.gen.disable()
        response, prosody = self.gen.generate("plain content", EmotionCategory.JOY)
        self.assertEqual(response, "plain content")


# ---------------------------------------------------------------------------
# PAD Vector Space
# ---------------------------------------------------------------------------

class TestPADVector(unittest.TestCase):
    def test_clamps_values(self):
        v = PADVector(pleasure=5.0, arousal=-5.0, dominance=2.0)
        self.assertEqual(v.pleasure, 1.0)
        self.assertEqual(v.arousal, -1.0)
        self.assertEqual(v.dominance, 1.0)

    def test_distance_same_vector(self):
        v = PADVector(0.5, 0.3, 0.1)
        self.assertAlmostEqual(v.distance(v), 0.0)

    def test_blend(self):
        a = PADVector(0.0, 0.0, 0.0)
        b = PADVector(1.0, 1.0, 1.0)
        mid = a.blend(b, 0.5)
        self.assertAlmostEqual(mid.pleasure, 0.5)

    def test_as_tuple(self):
        v = PADVector(0.1, 0.2, 0.3)
        self.assertEqual(v.as_tuple(), (0.1, 0.2, 0.3))


class TestPADSpace(unittest.TestCase):
    def setUp(self):
        self.space = PADSpace()
        self.space.enable()

    def test_update_from_emotion(self):
        result = self.space.update_from_emotion(EmotionCategory.JOY, intensity=1.0)
        self.assertGreater(result.pleasure, 0)

    def test_decay_toward_neutral(self):
        self.space.update_from_emotion(EmotionCategory.JOY, intensity=1.0)
        before = self.space.current.pleasure
        self.space.decay()
        self.assertLess(self.space.current.pleasure, before)

    def test_get_nearest_emotion(self):
        self.space.update_from_emotion(EmotionCategory.JOY, intensity=1.0, blend_alpha=1.0)
        nearest = self.space.get_nearest_emotion()
        self.assertIsNotNone(nearest)

    def test_map_emotion_to_pad(self):
        pad = self.space.map_emotion_to_pad(EmotionCategory.JOY)
        self.assertIsNotNone(pad)
        self.assertGreater(pad.pleasure, 0)

    def test_all_emotions_have_pad_mapping(self):
        for emotion in [EmotionCategory.JOY, EmotionCategory.DISTRESS,
                        EmotionCategory.FEAR, EmotionCategory.ANGER]:
            self.assertIn(emotion, EMOTION_PAD_MAP)


# ---------------------------------------------------------------------------
# Multimodal Emotion Recognition
# ---------------------------------------------------------------------------

class TestSpeechProsodyAnalyzer(unittest.TestCase):
    def test_high_pitch_high_energy_positive(self):
        analyzer = SpeechProsodyAnalyzer()
        result = analyzer.analyze(pitch_hz=250, rate_wpm=160, energy_db=-10)
        self.assertIsNotNone(result.emotion)
        self.assertGreater(result.confidence, 0)

    def test_low_pitch_low_energy(self):
        analyzer = SpeechProsodyAnalyzer()
        result = analyzer.analyze(pitch_hz=80, rate_wpm=90, energy_db=-50)
        self.assertIsNotNone(result.emotion)


class TestTextSentimentAnalyzer(unittest.TestCase):
    def test_positive_text(self):
        analyzer = TextSentimentAnalyzer()
        result = analyzer.analyze("I am so happy and excited today!")
        self.assertGreater(result.valence, 0)

    def test_negative_text(self):
        analyzer = TextSentimentAnalyzer()
        result = analyzer.analyze("I feel terrible and frustrated")
        self.assertLess(result.valence, 0)

    def test_negation(self):
        analyzer = TextSentimentAnalyzer()
        result = analyzer.analyze("I am not happy")
        self.assertLessEqual(result.valence, 0)


class TestFacialExpressionAnalyzer(unittest.TestCase):
    def test_no_image_returns_neutral(self):
        analyzer = FacialExpressionAnalyzer()
        result = analyzer.analyze(None)
        self.assertEqual(result.confidence, 0.0)

    def test_with_image_data(self):
        analyzer = FacialExpressionAnalyzer()
        result = analyzer.analyze(b"fake_image_data")
        self.assertGreater(result.confidence, 0)


class TestMultimodalEmotionRecognizer(unittest.TestCase):
    def setUp(self):
        self.recognizer = MultimodalEmotionRecognizer()
        self.recognizer.enable()

    def test_recognize_returns_result(self):
        result = self.recognizer.recognize(text="I am happy today")
        self.assertIsNotNone(result)

    def test_recognize_has_modality_weights(self):
        result = self.recognizer.recognize(text="test")
        self.assertIn("speech", result.modality_weights)
        self.assertIn("text", result.modality_weights)
        self.assertIn("face", result.modality_weights)

    def test_confidence_range(self):
        result = self.recognizer.recognize(text="I feel great!")
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)


# ---------------------------------------------------------------------------
# EPITOME Framework
# ---------------------------------------------------------------------------

class TestEPITOMEFramework(unittest.TestCase):
    def setUp(self):
        self.framework = EPITOMEFramework()
        self.framework.enable()

    def test_process_returns_response_and_context(self):
        response, context = self.framework.process(
            "I'm really worried about this",
            EmotionCategory.FEAR,
            0.8
        )
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        self.assertIsInstance(context, EPITOMEContext)

    def test_all_phases_produce_responses(self):
        _, context = self.framework.process("test input", EmotionCategory.DISTRESS)
        self.assertIn("reaction", context.phase_responses)
        self.assertIn("interpretation", context.phase_responses)
        self.assertIn("exploration", context.phase_responses)

    def test_reaction_phase_validates_emotion(self):
        phase = EmotionalReactionPhase()
        context = EPITOMEContext("I'm scared", EmotionCategory.FEAR)
        response = phase.process(context)
        self.assertIn("worried", response.lower())

    def test_interpretation_phase_identifies_need(self):
        phase = InterpretationPhase()
        context = EPITOMEContext("I need help with this", EmotionCategory.DISTRESS)
        response = phase.process(context)
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_exploration_phase_suggests_support(self):
        phase = ExplorationPhase()
        context = EPITOMEContext("I'm angry", EmotionCategory.ANGER)
        response = phase.process(context)
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)

    def test_generate_phase_response(self):
        _, context = self.framework.process("test", EmotionCategory.JOY)
        reaction = self.framework.generate_phase_response("reaction", context)
        self.assertIsInstance(reaction, str)


# ---------------------------------------------------------------------------
# Metacognitive Layer
# ---------------------------------------------------------------------------

class TestResponseQualityEvaluator(unittest.TestCase):
    def test_good_response_scores_high(self):
        evaluator = ResponseQualityEvaluator()
        score = evaluator.evaluate("Here is the information you requested about the weather today.")
        self.assertGreater(score, 0.7)

    def test_too_short_scores_low(self):
        evaluator = ResponseQualityEvaluator()
        score = evaluator.evaluate("Ok")
        self.assertLess(score, 0.5)

    def test_too_long_penalized(self):
        evaluator = ResponseQualityEvaluator()
        long_response = " ".join(["word"] * 150)
        score = evaluator.evaluate(long_response)
        self.assertLess(score, 1.0)


class TestErrorDetector(unittest.TestCase):
    def test_detects_incomplete_sentence(self):
        detector = ErrorDetector()
        errors = detector.detect("This is incomplete")
        self.assertTrue(any("incomplete" in e.lower() or "punctuation" in e.lower()
                            for e in errors))

    def test_no_errors_in_clean_response(self):
        detector = ErrorDetector()
        errors = detector.detect("The weather today is sunny and warm.")
        self.assertEqual(errors, [])

    def test_correct_adds_punctuation(self):
        detector = ErrorDetector()
        corrected = detector.correct("Missing punctuation", ["incomplete"])
        self.assertTrue(corrected.endswith("."))


class TestEmotionalAppropriatenessChecker(unittest.TestCase):
    def test_positive_response_for_distress_is_inappropriate(self):
        checker = EmotionalAppropriatenessChecker()
        appropriate, suggestion = checker.check(
            "That's great and wonderful!", EmotionCategory.DISTRESS
        )
        self.assertFalse(appropriate)
        self.assertIsNotNone(suggestion)

    def test_appropriate_response_for_joy(self):
        checker = EmotionalAppropriatenessChecker()
        appropriate, _ = checker.check("That's fantastic!", EmotionCategory.JOY)
        self.assertTrue(appropriate)

    def test_none_emotion_always_appropriate(self):
        checker = EmotionalAppropriatenessChecker()
        appropriate, _ = checker.check("anything", None)
        self.assertTrue(appropriate)


class TestSelfReflectionEngine(unittest.TestCase):
    def test_reflect_logs_entry(self):
        engine = SelfReflectionEngine()
        engine.reflect("input", "response", 0.8, [])
        self.assertEqual(len(engine.get_reflection_log()), 1)

    def test_reflect_low_quality_mentions_score(self):
        engine = SelfReflectionEngine()
        result = engine.reflect("input", "bad", 0.3, ["error1"])
        self.assertIn("0.3", result)

    def test_clear_log(self):
        engine = SelfReflectionEngine()
        engine.reflect("input", "response", 0.8, [])
        engine.clear_log()
        self.assertEqual(len(engine.get_reflection_log()), 0)


class TestMetacognitiveLayer(unittest.TestCase):
    def setUp(self):
        self.layer = MetacognitiveLayer()
        self.layer.enable()

    def test_evaluate_returns_report(self):
        report = self.layer.evaluate(
            "What's the weather?",
            "The weather today is sunny and warm.",
            EmotionCategory.JOY
        )
        self.assertGreater(report.score, 0)

    def test_evaluate_detects_emotional_mismatch(self):
        report = self.layer.evaluate(
            "I'm sad",
            "That's great and wonderful!",
            EmotionCategory.DISTRESS
        )
        self.assertFalse(report.emotionally_appropriate)

    def test_evaluate_suggests_correction(self):
        report = self.layer.evaluate(
            "test",
            "Incomplete sentence without punctuation",
            None
        )
        self.assertIsNotNone(report.corrected_response)


if __name__ == "__main__":
    unittest.main()
