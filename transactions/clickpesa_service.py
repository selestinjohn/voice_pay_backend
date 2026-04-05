import requests
from django.conf import settings


class ClickPesaService:
    @staticmethod
    def get_token():
        base_url = getattr(settings, "CLICKPESA_BASE_URL", None)
        client_id = getattr(settings, "CLICKPESA_CLIENT_ID", None)
        api_key = getattr(settings, "CLICKPESA_API_KEY", None)

        if not base_url:
            raise Exception("CLICKPESA_BASE_URL is missing in settings")
        if not client_id:
            raise Exception("CLICKPESA_CLIENT_ID is missing in settings")
        if not api_key:
            raise Exception("CLICKPESA_API_KEY is missing in settings")

        url = f"{base_url.rstrip('/')}/generate-token"

        response = requests.post(
            url,
            headers={
                "client-id": client_id,
                "api-key": api_key,
            },
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        token = data.get("token")

        if not token:
            raise Exception("ClickPesa token not found in response")

        return token

    @staticmethod
    def build_checksum(amount, phone_number, currency, order_reference):
        raise Exception(
            "ClickPesa checksum is not configured yet. Add the correct checksum formula in build_checksum()."
        )

    @staticmethod
    def preview_mobile_money_payout(phone_number, amount, order_reference, currency="TZS"):
        token = ClickPesaService.get_token()
        checksum = ClickPesaService.build_checksum(
            amount=amount,
            phone_number=phone_number,
            currency=currency,
            order_reference=order_reference,
        )

        url = f"{settings.CLICKPESA_BASE_URL.rstrip('/')}/payouts/preview-mobile-money-payout"

        payload = {
            "amount": amount,
            "phoneNumber": phone_number,
            "currency": currency,
            "orderReference": order_reference,
            "checksum": checksum,
        }

        response = requests.post(
            url,
            headers={
                "Authorization": token,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def create_mobile_money_payout(phone_number, amount, order_reference, currency="TZS"):
        token = ClickPesaService.get_token()
        checksum = ClickPesaService.build_checksum(
            amount=amount,
            phone_number=phone_number,
            currency=currency,
            order_reference=order_reference,
        )

        url = f"{settings.CLICKPESA_BASE_URL.rstrip('/')}/payouts/create-mobile-money-payout"

        payload = {
            "amount": amount,
            "phoneNumber": phone_number,
            "currency": currency,
            "orderReference": order_reference,
            "checksum": checksum,
        }

        response = requests.post(
            url,
            headers={
                "Authorization": token,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def query_payout_status(order_reference):
        token = ClickPesaService.get_token()
        url = f"{settings.CLICKPESA_BASE_URL.rstrip('/')}/payouts/{order_reference}"

        response = requests.get(
            url,
            headers={
                "Authorization": token,
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()