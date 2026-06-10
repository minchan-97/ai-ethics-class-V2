"""
ethics_engine_v2.py — AI 윤리 수업용 고도화 엔진
=================================================
기본: 키워드 탐지
고도화: NeuralMarkov logP 결합
두 신호를 합쳐서 더 정확한 판정
"""
from __future__ import annotations
from ethics_engine import RuleGuardrail, VIOLATION_PATTERNS
import time

try:
    from neural_markov_engine import NeuralMarkovEngine
    MARKOV_OK = True
except Exception:
    MARKOV_OK = False


class RuleGuardrailV2(RuleGuardrail):
    """
    키워드 탐지 + NeuralMarkov logP 결합 엔진
    기존 RuleGuardrail 상속 → 기능 추가
    """
    def __init__(self, category: str = "환각"):
        super().__init__(category)
        self.markov = NeuralMarkovEngine() if MARKOV_OK else None
        self.markov_trained = False
        self.markov_available = MARKOV_OK

    def train(self, guideline_text: str, markov_epochs: int = 10):
        """키워드 학습 + NeuralMarkov 학습"""
        # 기존 키워드 학습
        super().train(guideline_text)

        # NeuralMarkov 학습
        if self.markov and len(guideline_text.strip()) > 20:
            try:
                self.markov.train(
                    guideline_text,
                    embedding_dim=32,
                    epochs=markov_epochs,
                )
                self.markov_trained = True
            except Exception:
                self.markov_trained = False

    def evaluate(self, ai_answer: str) -> dict:
        """키워드 + NeuralMarkov 결합 판정"""
        t0 = time.perf_counter()

        # 1단계: 키워드 탐지
        kw_result = super().evaluate(ai_answer)

        # 2단계: NeuralMarkov logP
        markov_result = None
        if self.markov and self.markov_trained:
            try:
                markov_result = self.markov.evaluate(ai_answer)
            except Exception:
                markov_result = None

        # 결합 판정
        if markov_result:
            kw_verdict = kw_result["verdict"]
            mk_verdict = markov_result.get("status", "SKIP")

            # 두 신호 결합
            # 둘 다 PASS → PASS
            # 하나라도 FATAL → FATAL
            # 나머지 → WARNING
            if kw_verdict == "PASS" and mk_verdict == "PASS":
                final_verdict = "PASS"
            elif kw_verdict == "FATAL" or mk_verdict == "FATAL":
                final_verdict = "FATAL"
            elif kw_verdict == "WARNING" or mk_verdict == "WARNING":
                final_verdict = "WARNING"
            else:
                final_verdict = kw_verdict

            ms = (time.perf_counter() - t0) * 1000
            return {
                **kw_result,
                "verdict": final_verdict,
                "kw_verdict": kw_verdict,
                "mk_verdict": mk_verdict,
                "logp": markov_result.get("avg_logp", 0),
                "markov_used": True,
                "ms": ms,
            }

        ms = (time.perf_counter() - t0) * 1000
        return {
            **kw_result,
            "kw_verdict": kw_result["verdict"],
            "mk_verdict": "미학습",
            "logp": None,
            "markov_used": False,
            "ms": ms,
        }
