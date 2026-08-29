import hmac
import hashlib
import requests
from typing import Dict, Any, Optional, List
from backend.app.core.config import settings

class RazorpayService:
    def __init__(self):
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
        
        self.is_configured = bool(self.key_id and self.key_id.strip() and self.key_secret and self.key_secret.strip())
        if self.is_configured:
            print("Razorpay service initialized.")
        else:
            print("Razorpay service initialized in SIMULATED MOCK MODE.")

    def verify_connection(self) -> Dict[str, Any]:
        """
        Verify credentials by querying a safe, read-only Razorpay API endpoint.
        Enforces a safety guard to block live credentials.
        """
        if not self.is_configured:
            return {
                "connected": False,
                "mode": "test",
                "error": "Razorpay credentials are not configured in the backend environment."
            }

        # Safety Guard: Ensure only Test Mode credentials are used
        if not self.key_id.startswith("rzp_test_"):
            return {
                "connected": False,
                "mode": "live_blocked",
                "error": "Only Razorpay Test Mode credentials are allowed. Live production credentials blocked for safety."
            }

        url = "https://api.razorpay.com/v1/payments?count=1"
        auth = (self.key_id, self.key_secret)
        
        try:
            response = requests.get(url, auth=auth, timeout=10)
            if response.status_code == 200:
                masked_id = f"{self.key_id[:9]}****{self.key_id[-4:]}" if len(self.key_id) > 9 else self.key_id
                return {
                    "connected": True,
                    "mode": "test",
                    "key_id_masked": masked_id
                }
            else:
                return {
                    "connected": False,
                    "mode": "test",
                    "error": f"Authentication failed: Razorpay API returned HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                "connected": False,
                "mode": "test",
                "error": f"Network connection failure: {str(e)}"
            }

    def fetch_payments(self, count: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch the list of recent payments from Razorpay API.
        Enforces test-mode-only safety checks.
        """
        if not self.is_configured:
            raise ValueError("Razorpay credentials are not configured.")

        if not self.key_id.startswith("rzp_test_"):
            raise ValueError("Only Razorpay Test Mode credentials are allowed.")

        url = f"https://api.razorpay.com/v1/payments?count={count}"
        auth = (self.key_id, self.key_secret)
        
        response = requests.get(url, auth=auth, timeout=10)
        if response.status_code == 200:
            return response.json().get("items", [])
        else:
            raise Exception(f"Razorpay API returned HTTP {response.status_code}: {response.text}")

    def create_payment_link(
        self,
        amount: float,
        reference_id: str,
        customer_name: str,
        customer_email: str,
        customer_phone: Optional[str] = None,
        description: str = "Payment recovery via RecoverAI"
    ) -> Dict[str, Any]:
        """
        Creates a payment link via official Razorpay API.
        Amount must be in paise (so ₹1.00 = 100 paise).
        """
        amount_paise = int(round(amount * 100))
        
        if not self.is_configured:
            # Fallback mock payment link for demo purposes
            fake_link_id = f"plink_{reference_id}_{hash(reference_id) % 10000}"
            return {
                "id": fake_link_id,
                "short_url": f"https://rzp.io/i/mock_{fake_link_id}",
                "status": "created",
                "amount": amount_paise,
                "currency": "INR",
                "reference_id": reference_id,
                "simulated": True
            }

        # Safety Guard: Ensure only Test Mode credentials are used
        if not self.key_id.startswith("rzp_test_"):
            raise ValueError("Only Razorpay Test Mode credentials are allowed.")

        # Live Razorpay Test Mode request
        url = "https://api.razorpay.com/v1/payment_links"
        auth = (self.key_id, self.key_secret)
        
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "accept_partial": False,
            "reference_id": reference_id,
            "description": description,
            "customer": {
                "name": customer_name,
                "email": customer_email,
                "contact": customer_phone or "+919999999999"
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": True,
            "callback_url": f"{settings.FRONTEND_URL}/payment-success?reference_id={reference_id}",
            "callback_method": "get"
        }
        
        try:
            response = requests.post(url, json=payload, auth=auth, timeout=10)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Razorpay API error: {response.status_code} - {response.text}")
                # Fallback on failure
                return {
                    "id": f"plink_err_{reference_id}",
                    "short_url": "https://rzp.io/i/mock_error_link",
                    "status": "failed",
                    "error": response.text
                }
        except Exception as e:
            print(f"Connection error to Razorpay: {e}")
            raise e

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """
        Verify Razorpay Webhook Signature using HMAC-SHA256.
        """
        if not self.webhook_secret or not self.webhook_secret.strip():
            # If no secret configured locally, we log a warning but allow for mock developer test
            print("WARNING: RAZORPAY_WEBHOOK_SECRET is empty. Signature verification skipped for testing.")
            return True
            
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                raw_body,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            print(f"Error validating signature: {e}")
            return False
