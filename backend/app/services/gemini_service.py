import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from google import genai
from google.genai import types

from backend.app.core.config import settings

# Structured schema model for recovery decision
class RecoveryDecision(BaseModel):
    classification: Literal["temporary_failure", "permanent_failure", "fraud_suspected"]
    failure_reason: str
    recovery_probability: float = Field(..., ge=0.0, le=1.0)
    recommended_action: Literal["RETRY", "PAYMENT_LINK", "REMINDER", "MANUAL_REVIEW", "STOP"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    explanation: str
    customer_action_required: bool
    policy_considerations: str

class GeminiService:
    # Memory cache for active models
    _active_model: Optional[str] = None
    _verified_models: List[Dict[str, Any]] = []
    _last_verified_at: Optional[str] = None
    _init_done: bool = False

    @staticmethod
    def get_client() -> Optional[genai.Client]:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or not api_key.strip():
            return None
        try:
            return genai.Client(api_key=api_key)
        except Exception:
            return None

    @classmethod
    def _is_text_model(cls, name: str) -> bool:
        name_lower = name.lower()
        if "gemini" not in name_lower:
            return False
        # Exclusions for image, embedding, live streaming, tts, robotics models
        exclusions = ["embedding", "image", "tts", "live", "translate", "audio", "robotics", "computer-use", "deep-research", "veo", "lyria", "clip"]
        for exc in exclusions:
            if exc in name_lower:
                return False
        return True

    @classmethod
    def list_available_models(cls) -> List[Dict[str, Any]]:
        """List and query the model catalog available to the active key."""
        client = cls.get_client()
        if not client:
            return []
        try:
            models = client.models.list()
            results = []
            for m in models:
                m_name = m.name
                if m_name.startswith("models/"):
                    m_name = m_name[7:]
                if cls._is_text_model(m_name):
                    results.append({
                        "name": m_name,
                        "display_name": m.display_name,
                        "description": getattr(m, "description", "")
                    })
            return results
        except Exception as e:
            print(f"Failed to list models: {e}")
            return []

    @classmethod
    def verify_model_compatibility(cls, model_name: str) -> Dict[str, Any]:
        """Perform a harmless test structured generation request to verify compatibility."""
        client = cls.get_client()
        if not client:
            return {"verified": False, "error": "GEMINI: NOT CONFIGURED"}
        
        class TestSchema(BaseModel):
            status: Literal["ok", "error"]
            explanation: str

        try:
            #Harmless prompt check
            response = client.models.generate_content(
                model=model_name,
                contents="Verify connection. Return status ok.",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TestSchema,
                    temperature=0.1
                )
            )
            if response and response.text:
                data = json.loads(response.text.strip())
                # Validate using schema
                parsed = TestSchema(**data)
                if parsed.status == "ok":
                    return {"verified": True, "error": None}
            return {"verified": False, "error": "Empty or invalid response structure."}
        except Exception as e:
            return {"verified": False, "error": str(e)}

    @classmethod
    def initialize_models(cls) -> None:
        """Runs the auto-discovery on startup to select the best active model."""
        if cls._init_done:
            return
        cls._init_done = True
        
        client = cls.get_client()
        if not client:
            return

        try:
            discovered = cls.list_available_models()
            candidates = [d["name"] for d in discovered]

            env_pref = os.getenv("GEMINI_MODEL", "").strip()
            if env_pref.startswith("models/"):
                env_pref = env_pref[7:]

            sorted_candidates = []
            if env_pref and env_pref in candidates:
                sorted_candidates.append(env_pref)

            # Prioritize standard flash models
            flash = sorted([c for c in candidates if "flash" in c and "lite" not in c], reverse=True)
            sorted_candidates.extend(flash)

            # Prioritize pro models
            pro = sorted([c for c in candidates if "pro" in c], reverse=True)
            sorted_candidates.extend(pro)

            # Flash lite
            lite = sorted([c for c in candidates if "lite" in c], reverse=True)
            sorted_candidates.extend(lite)

            # Deduplicate
            seen = set()
            sorted_candidates = [c for c in sorted_candidates if not (c in seen or seen.add(c))]

            # Verify top 3 candidates at boot
            verified_list = []
            for candidate in sorted_candidates[:3]:
                print(f"Discovering and testing model: {candidate}")
                test_status = cls.verify_model_compatibility(candidate)
                if test_status["verified"]:
                    verified_list.append({
                        "name": candidate,
                        "verified": True,
                        "supports_recoverai": True
                    })
                    if not cls._active_model:
                        cls._active_model = candidate
                        cls._last_verified_at = datetime.utcnow().isoformat()
            cls._verified_models = verified_list
        except Exception as e:
            print(f"Error during model initialization: {e}")

    @classmethod
    def get_active_model(cls) -> Optional[str]:
        """Get the current active model, initializing if not done yet."""
        if not cls._active_model:
            cls.initialize_models()
        return cls._active_model

    @classmethod
    def set_active_model(cls, model_name: str) -> bool:
        """Select a verified compatible model to make it active."""
        if model_name.startswith("models/"):
            model_name = model_name[7:]
        status = cls.verify_model_compatibility(model_name)
        if status["verified"]:
            cls._active_model = model_name
            cls._last_verified_at = datetime.utcnow().isoformat()
            # Upsert into verified cache list
            if not any(vm["name"] == model_name for vm in cls._verified_models):
                cls._verified_models.append({
                    "name": model_name,
                    "verified": True,
                    "supports_recoverai": True
                })
            return True
        return False

    @classmethod
    def verify_connection(cls) -> Dict[str, Any]:
        """Verify Gemini connection using the active model."""
        active_model = cls.get_active_model()
        if not active_model:
            return {
                "connected": False,
                "error": "GEMINI: NOT CONFIGURED",
                "active_model": None,
                "sdk": "google-genai",
                "last_verified_at": None
            }
        
        status = cls.verify_model_compatibility(active_model)
        if status["verified"]:
            return {
                "connected": True,
                "error": None,
                "active_model": active_model,
                "sdk": "google-genai",
                "last_verified_at": cls._last_verified_at
            }
        else:
            return {
                "connected": False,
                "error": status["error"] or "Validation failed",
                "active_model": active_model,
                "sdk": "google-genai",
                "last_verified_at": None
            }

    @classmethod
    def make_recovery_decision(
        cls,
        tx_id: str,
        amount: float,
        payment_method: str,
        failure_code: str,
        retry_count: int,
        customer_email: str,
        customer_spending_history: float
    ) -> Dict[str, Any]:
        """
        Formulate recovery recommendation with automatic model fallback.
        Requests structured output and validates with Pydantic.
        """
        active_model = cls.get_active_model()
        if not active_model:
            raise ValueError("GEMINI: NOT CONFIGURED")

        # Assemble models fallback list
        candidates_to_try = [active_model]
        for vm in cls._verified_models:
            v_name = vm["name"]
            if v_name not in candidates_to_try:
                candidates_to_try.append(v_name)

        # Fallback to general list if verified list is empty
        if len(candidates_to_try) <= 1:
            discovered = cls.list_available_models()
            for d in discovered:
                d_name = d["name"]
                if d_name not in candidates_to_try:
                    candidates_to_try.append(d_name)

        prompt = f"""
        Analyze this payment failure and formulate a structured recovery strategy.
        - Transaction ID: {tx_id}
        - Amount: {amount} INR
        - Payment Method: {payment_method}
        - Failure Signal: {failure_code}
        - Previous Interventions / Retry Count: {retry_count}
        - Customer Email: {customer_email}
        - Customer Lifetime Value (LTV): {customer_spending_history} INR
        
        Rules:
        1. recommended_action can be RETRY, PAYMENT_LINK, REMINDER, MANUAL_REVIEW, or STOP.
        2. RETRY is only for temporary failures.
        3. STOP is for fraud risk or permanent declines.
        4. MANUAL_REVIEW is for high value dropoffs.
        """

        client = cls.get_client()
        if not client:
            raise ValueError("GEMINI: NOT CONFIGURED")

        last_error = None
        for current_model in candidates_to_try:
            try:
                print(f"Calling Gemini Recovery Decision using model: {current_model}")
                response = client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RecoveryDecision,
                        temperature=0.1
                    )
                )

                if not response or not response.text:
                    raise RuntimeError("Empty response received from Gemini API")

                # Parse and validate response
                data = json.loads(response.text.strip())
                decision = RecoveryDecision(**data)
                
                return {
                    "recommended_action": decision.recommended_action,
                    "confidence": decision.confidence,
                    "explanation": decision.explanation,
                    "failure_classification": decision.classification,
                    "model_name": current_model,
                    "is_mock": False,
                    "risk_level": decision.risk_level,
                    "customer_action_required": decision.customer_action_required,
                    "policy_considerations": decision.policy_considerations,
                    "failure_reason": decision.failure_reason,
                    "recovery_probability": decision.recovery_probability
                }

            except ValidationError as ve:
                # Attempt one retry with a stricter structured prompt
                print(f"Validation failed on model {current_model}: {ve}. Retrying once...")
                try:
                    retry_prompt = prompt + "\nEnsure all JSON properties match the expected schema precisely."
                    retry_response = client.models.generate_content(
                        model=current_model,
                        contents=retry_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=RecoveryDecision,
                            temperature=0.0
                        )
                    )
                    data = json.loads(retry_response.text.strip())
                    decision = RecoveryDecision(**data)
                    return {
                        "recommended_action": decision.recommended_action,
                        "confidence": decision.confidence,
                        "explanation": decision.explanation,
                        "failure_classification": decision.classification,
                        "model_name": current_model,
                        "is_mock": False,
                        "risk_level": decision.risk_level,
                        "customer_action_required": decision.customer_action_required,
                        "policy_considerations": decision.policy_considerations,
                        "failure_reason": decision.failure_reason,
                        "recovery_probability": decision.recovery_probability
                    }
                except Exception as retry_err:
                    last_error = retry_err
            except Exception as e:
                last_error = e
                # Check for fatal authorization issues, which we do NOT fallback on
                err_msg = str(e).lower()
                if "api key" in err_msg or "unauthorized" in err_msg or "invalid" in err_msg:
                    raise e
                print(f"Model {current_model} failed: {e}. Trying next verified fallback...")

        raise last_error or RuntimeError("Gemini model execution failed.")
