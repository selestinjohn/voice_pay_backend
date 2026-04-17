import hashlib
import hmac
import json
import time
import uuid

import requests
from django.conf import settings


class SnippeService:
    @staticmethod
    def get_base_url():
        return getattr(settings, "SNIPPE_BASE_URL", "https://api.snippe.sh").rstrip("/")

    @staticmethod
    def get_api_key():
        api_key = getattr(settings, "SNIPPE_API_KEY", "")
        if not api_key:
            raise Exception("SNIPPE_API_KEY is missing in settings")
        return api_key

    @staticmethod
    def get_webhook_url():
        webhook_url = getattr(settings, "SNIPPE_WEBHOOK_URL", "")
        if not webhook_url:
            raise Exception("SNIPPE_WEBHOOK_URL is missing in settings")
        return webhook_url

    @staticmethod
    def _headers(idempotency_key=None):
        headers = {
            "Authorization": f"Bearer {SnippeService.get_api_key()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def normalize_phone(phone_number: str) -> str:
        phone = (phone_number or "").strip().replace(" ", "")

        if phone.startswith("+255") and len(phone) == 13:
            return phone[1:]
        if phone.startswith("255") and len(phone) == 12:
            return phone
        if phone.startswith("0") and len(phone) == 10:
            return f"255{phone[1:]}"

        raise ValueError("Invalid Tanzanian phone number format")

    @staticmethod
    def split_name(full_name: str):
        name = (full_name or "").strip()
        if not name:
            return "Customer", "User"

        parts = name.split()
        if len(parts) == 1:
            return parts[0], "User"

        return parts[0], " ".join(parts[1:])

    @staticmethod
    def create_mobile_payment(
        phone_number: str,
        amount: int,
        currency: str = "TZS",
        customer_name: str | None = None,
        customer_email: str | None = None,
        metadata: dict | None = None,
        webhook_url: str | None = None,
    ):
        if amount is None or int(amount) <= 0:
            raise ValueError("Amount must be greater than zero")

        firstname, lastname = SnippeService.split_name(customer_name or "")

        url = f"{SnippeService.get_base_url()}/v1/payments"
        idempotency_key = str(uuid.uuid4())

        payload = {
            "payment_type": "mobile",
            "details": {
                "amount": int(amount),
                "currency": currency,
            },
            "phone_number": SnippeService.normalize_phone(phone_number),
            "customer": {
                "firstname": firstname,
                "lastname": lastname,
                "email": customer_email or "customer@voicepay.local",
            },
            "webhook_url": webhook_url or SnippeService.get_webhook_url(),
            "metadata": metadata or {},
        }

        response = requests.post(
            url,
            headers=SnippeService._headers(idempotency_key=idempotency_key),
            json=payload,
            timeout=30,
        )

        if not response.ok:
            raise Exception(
                f"Snippe payment failed: {response.status_code} - {response.text}"
            )

        return response.json()

    @staticmethod
    def create_mobile_payout(
        recipient_phone: str,
        recipient_name: str,
        amount: int,
        narration: str,
        metadata: dict | None = None,
        webhook_url: str | None = None,
    ):
        if amount is None or int(amount) <= 0:
            raise ValueError("Amount must be greater than zero")

        url = f"{SnippeService.get_base_url()}/v1/payouts/send"
        idempotency_key = str(uuid.uuid4())

        payload = {
            "amount": int(amount),
            "channel": "mobile",
            "recipient_phone": SnippeService.normalize_phone(recipient_phone),
            "recipient_name": recipient_name,
            "narration": narration,
            "webhook_url": webhook_url or SnippeService.get_webhook_url(),
            "metadata": metadata or {},
        }

        response = requests.post(
            url,
            headers=SnippeService._headers(idempotency_key=idempotency_key),
            json=payload,
            timeout=30,
        )

        if not response.ok:
            raise Exception(
                f"Snippe payout failed: {response.status_code} - {response.text}"
            )

        return response.json()

    @staticmethod
    def get_payout_status(reference: str):
        url = f"{SnippeService.get_base_url()}/v1/payouts/{reference}"
        response = requests.get(
            url,
            headers=SnippeService._headers(),
            timeout=30,
        )

        if not response.ok:
            raise Exception(
                f"Snippe payout status failed: {response.status_code} - {response.text}"
            )

        return response.json()

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, headers) -> bool:
        signing_key = getattr(settings, "SNIPPE_WEBHOOK_SECRET", "")
        if not signing_key:
            return False

        timestamp = headers.get("X-Webhook-Timestamp")
        signature = headers.get("X-Webhook-Signature")

        if not timestamp or not signature:
            return False

        try:
            event_time = int(timestamp)
        except (TypeError, ValueError):
            return False

        current_time = int(time.time())
        if abs(current_time - event_time) > 300:
            return False

        payload_text = raw_body.decode("utf-8")
        message = f"{timestamp}.{payload_text}"

        expected_signature = hmac.new(
            signing_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    @staticmethod
    def parse_webhook(raw_body: bytes):
        try:
            return json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"Invalid webhook JSON: {exc}") from exc

    @staticmethod
    def extract_event_fields(event: dict) -> dict:
        if "data" in event and isinstance(event["data"], dict):
            data = event["data"]
            return {
                "event_id": event.get("id"),
                "event_type": event.get("type"),
                "reference": data.get("reference"),
                "external_reference": data.get("external_reference"),
                "status": data.get("status"),
                "provider": ((data.get("channel") or {}).get("provider")),
                "amount": ((data.get("amount") or {}).get("value")),
                "currency": ((data.get("amount") or {}).get("currency")),
                "phone": (
                    ((data.get("customer") or {}).get("phone"))
                    or ((data.get("recipient") or {}).get("phone"))
                ),
                "metadata": data.get("metadata") or {},
                "raw": event,
            }

        return {
            "event_id": event.get("id"),
            "event_type": event.get("event") or event.get("type"),
            "reference": event.get("reference"),
            "external_reference": event.get("external_reference"),
            "status": event.get("status"),
            "provider": event.get("payment_channel"),
            "amount": ((event.get("amount") or {}).get("value")),
            "currency": ((event.get("amount") or {}).get("currency")),
            "phone": (
                ((event.get("customer") or {}).get("phone"))
                or ((event.get("recipient") or {}).get("phone"))
            ),
            "metadata": event.get("metadata") or {},
            "raw": event,
        }