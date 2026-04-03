import requests
from django.conf import settings


class ClickPesaService:
    @staticmethod
    def get_token():
        url = f"{settings.CLICKPESA_BASE_URL}/generate-token"

        response = requests.post(
            url,
            headers={
                "client-id": settings.CLICKPESA_CLIENT_ID,
                "api-key": settings.CLICKPESA_API_KEY,
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
        """
        TODO:
        Replace this with the EXACT checksum rule from your ClickPesa account/docs.
        The public docs we loaded show checksum is required, but not the formula.
        """
        raise NotImplementedError(
            "Add your ClickPesa checksum formula in build_checksum()."
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

        url = f"{settings.CLICKPESA_BASE_URL}/payouts/preview-mobile-money-payout"

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
                "Authorization": token,  # docs show returned token already includes Bearer prefix
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

        url = f"{settings.CLICKPESA_BASE_URL}/payouts/create-mobile-money-payout"

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
                "Authorization": token,  # docs show returned token already includes Bearer prefix
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
        url = f"{settings.CLICKPESA_BASE_URL}/payouts/{order_reference}"

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