import json
import re
import uuid

from rest_framework.decorators import api_view
from rest_framework.response import Response

from users.models import UserProfile
from .models import Transaction
from .serializers import TransactionSerializer
from .snippe_service import SnippeService


def get_request_data(request):
    try:
        if request.data:
            return request.data
    except Exception:
        pass

    try:
        body = request.body.decode("utf-8")
        if body:
            return json.loads(body)
    except Exception:
        pass

    return {}


def parse_command(text):
    text = (text or "").lower().strip()

    if text in ["yes", "confirm", "okay"]:
        return {"action": "confirm"}

    if text in ["no", "cancel"]:
        return {"action": "cancel"}

    if "balance" in text:
        return {"action": "check_balance"}

    if "send" in text:
        amount_match = re.findall(r"\d+", text)
        phone_match = re.findall(r"0\d{9}", text)

        amount = int(amount_match[0]) if amount_match else None
        phone = phone_match[0] if phone_match else None

        return {
            "action": "send_money",
            "amount": amount,
            "phone": phone,
        }

    return {"action": "unknown"}


@api_view(["POST"])
def register_user(request):
    try:
        data = get_request_data(request)

        name = data.get("name")
        phone = data.get("phone")
        passphrase = data.get("passphrase")

        if not name or not phone or not passphrase:
            return Response(
                {"success": False, "message": "Name, phone, and passphrase are required"},
                status=400,
            )

        if UserProfile.objects.filter(phone=phone).exists():
            return Response(
                {"success": False, "message": "Phone already exists"},
                status=400,
            )

        user = UserProfile.objects.create(
            name=name,
            phone=phone,
            passphrase=passphrase,
        )

        return Response(
            {
                "success": True,
                "message": "Registration successful",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "phone": user.phone,
                    "balance": user.balance,
                },
            },
            status=201,
        )
    except Exception as e:
        return Response(
            {"success": False, "stage": "register_user", "message": str(e)},
            status=500,
        )


@api_view(["POST"])
def login_user(request):
    try:
        data = get_request_data(request)
        phone = data.get("phone")
        passphrase = data.get("passphrase")

        if not phone or not passphrase:
            return Response(
                {"success": False, "message": "Phone and passphrase are required"},
                status=400,
            )

        try:
            user = UserProfile.objects.get(phone=phone)
        except UserProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "User not found"},
                status=404,
            )

        if user.passphrase != passphrase:
            return Response(
                {"success": False, "message": "Invalid passphrase"},
                status=400,
            )

        return Response(
            {
                "success": True,
                "message": f"Welcome {user.name}",
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "phone": user.phone,
                    "balance": user.balance,
                },
            },
            status=200,
        )
    except Exception as e:
        return Response(
            {"success": False, "stage": "login_user", "message": str(e)},
            status=500,
        )


@api_view(["POST"])
def check_balance(request):
    try:
        data = get_request_data(request)
        phone = data.get("phone")

        if not phone:
            return Response(
                {"success": False, "message": "Phone is required"},
                status=400,
            )

        try:
            user = UserProfile.objects.get(phone=phone)
        except UserProfile.DoesNotExist:
            return Response(
                {"success": False, "message": "User not found"},
                status=404,
            )

        return Response(
            {
                "success": True,
                "balance": user.balance,
                "message": f"Your balance is {user.balance} TZS",
            },
            status=200,
        )
    except Exception as e:
        return Response(
            {"success": False, "stage": "check_balance", "message": str(e)},
            status=500,
        )


@api_view(["POST"])
def process_voice(request):
    try:
        data = get_request_data(request)

        text = data.get("text")
        user_phone = data.get("user_phone")

        if not text:
            return Response({"success": False, "message": "No text provided"}, status=400)

        if not user_phone:
            return Response({"success": False, "message": "User phone is required"}, status=400)

        try:
            user = UserProfile.objects.get(phone=user_phone)
        except UserProfile.DoesNotExist:
            return Response({"success": False, "message": "User not found"}, status=404)

        parsed = parse_command(text)

        if parsed["action"] == "check_balance":
            return Response(
                {
                    "success": True,
                    "action": "check_balance",
                    "balance": user.balance,
                    "message": f"Your balance is {user.balance} TZS",
                },
                status=200,
            )

        if parsed["action"] == "send_money":
            if not parsed.get("amount"):
                return Response({"success": False, "message": "Specify amount"}, status=400)

            if not parsed.get("phone"):
                return Response(
                    {"success": False, "message": "Provide recipient phone number"},
                    status=400,
                )

            transaction = Transaction.objects.create(
                sender_phone=user_phone,
                receiver_phone=parsed["phone"],
                amount=parsed["amount"],
                action=Transaction.ACTION_SEND_MONEY,
                status=Transaction.STATUS_AWAITING_CONFIRMATION,
                voice_text=text,
                provider_name="snippe",
            )

            return Response(
                {
                    "success": True,
                    "action": "send_money",
                    "message": (
                        f"You want to send {parsed['amount']} TZS to {parsed['phone']}. "
                        f"Say confirm to continue or cancel to stop."
                    ),
                    "transaction_id": transaction.id,
                    "status": transaction.status,
                    "transaction": TransactionSerializer(transaction).data,
                },
                status=200,
            )

        if parsed["action"] == "confirm":
            latest_transaction = (
                Transaction.objects.filter(
                    sender_phone=user_phone,
                    status=Transaction.STATUS_AWAITING_CONFIRMATION,
                    action=Transaction.ACTION_SEND_MONEY,
                )
                .order_by("-created_at")
                .first()
            )

            if not latest_transaction:
                return Response(
                    {"success": False, "message": "No pending transaction found to confirm"},
                    status=404,
                )

            if not latest_transaction.collection_reference:
                latest_transaction.collection_reference = f"COL-{uuid.uuid4().hex[:12].upper()}"

            try:
                collection_response = SnippeService.create_mobile_payment(
                    phone_number=latest_transaction.sender_phone,
                    amount=latest_transaction.amount,
                    customer_name=user.name,
                    metadata={
                        "transaction_id": latest_transaction.id,
                        "sender_phone": latest_transaction.sender_phone,
                        "recipient_phone": latest_transaction.receiver_phone,
                        "flow": "wallet_to_wallet_collection",
                        "collection_reference": latest_transaction.collection_reference,
                    },
                )

                collection_data = collection_response.get("data") or {}

                latest_transaction.collection_response = collection_response
                latest_transaction.collection_status = (
                    collection_data.get("status")
                    or collection_response.get("status")
                    or "pending"
                )
                latest_transaction.status = Transaction.STATUS_PAYMENT_PENDING
                latest_transaction.provider_name = "snippe"
                latest_transaction.save()

                return Response(
                    {
                        "success": True,
                        "action": "confirm",
                        "message": (
                            "Payment request sent successfully. "
                            "Please check your phone and enter your mobile money PIN to continue."
                        ),
                        "transaction_id": latest_transaction.id,
                        "status": latest_transaction.status,
                        "collection_reference": latest_transaction.collection_reference,
                        "collection_status": latest_transaction.collection_status,
                    },
                    status=200,
                )
            except Exception as e:
                latest_transaction.status = Transaction.STATUS_FAILED
                latest_transaction.collection_status = "request_failed"
                latest_transaction.collection_response = {"error": str(e)}
                latest_transaction.save()

                return Response(
                    {
                        "success": False,
                        "action": "confirm",
                        "message": "Failed to initiate payment request",
                        "transaction_id": latest_transaction.id,
                        "error": str(e),
                    },
                    status=400,
                )

        if parsed["action"] == "cancel":
            latest_transaction = (
                Transaction.objects.filter(
                    sender_phone=user_phone,
                    status=Transaction.STATUS_AWAITING_CONFIRMATION,
                    action=Transaction.ACTION_SEND_MONEY,
                )
                .order_by("-created_at")
                .first()
            )

            if not latest_transaction:
                return Response(
                    {"success": False, "message": "No pending transaction found to cancel"},
                    status=404,
                )

            latest_transaction.status = Transaction.STATUS_CANCELLED
            latest_transaction.save()

            return Response(
                {
                    "success": True,
                    "action": "cancel",
                    "message": "Transaction cancelled successfully",
                    "transaction_id": latest_transaction.id,
                    "status": latest_transaction.status,
                },
                status=200,
            )

        return Response({"success": False, "message": "Command not recognized"}, status=400)

    except Exception as e:
        return Response(
            {"success": False, "stage": "process_voice", "message": str(e)},
            status=500,
        )


@api_view(["GET"])
def transaction_status(request, transaction_id):
    try:
        transaction = Transaction.objects.get(id=transaction_id)
        return Response(
            {
                "success": True,
                "transaction": TransactionSerializer(transaction).data,
            },
            status=200,
        )
    except Transaction.DoesNotExist:
        return Response({"success": False, "message": "Transaction not found"}, status=404)
    except Exception as e:
        return Response(
            {"success": False, "stage": "transaction_status", "message": str(e)},
            status=500,
        )


@api_view(["POST"])
def payment_webhook(request):
    try:
        raw_body = request.body

        try:
            signature_is_valid = SnippeService.verify_webhook_signature(
                raw_body=raw_body,
                headers=request.headers,
            )
        except Exception:
            signature_is_valid = False

        data = SnippeService.parse_webhook(raw_body)
        event = SnippeService.extract_event_fields(data)

        event_type = (event.get("event_type") or "").lower()
        provider_status = (event.get("status") or "").lower()
        metadata = event.get("metadata") or {}

        if event_type.startswith("payment."):
            transaction = None

            collection_reference = metadata.get("collection_reference")
            if collection_reference:
                transaction = Transaction.objects.filter(
                    collection_reference=collection_reference
                ).first()

            if not transaction and metadata.get("transaction_id"):
                transaction = Transaction.objects.filter(
                    id=metadata.get("transaction_id")
                ).first()

            if not transaction:
                return Response(
                    {"success": False, "message": "Collection transaction not found"},
                    status=404,
                )

            transaction.collection_response = event["raw"]
            transaction.collection_status = provider_status
            transaction.provider_name = "snippe"

            if event_type == "payment.completed":
                transaction.status = Transaction.STATUS_PROCESSING
                transaction.save()

                if not transaction.payout_reference:
                    try:
                        payout_response = SnippeService.create_mobile_payout(
                            recipient_phone=transaction.receiver_phone,
                            recipient_name=f"Recipient {transaction.receiver_phone}",
                            amount=transaction.amount,
                            narration=f"Voice Pay transfer from {transaction.sender_phone}",
                            metadata={
                                "transaction_id": transaction.id,
                                "sender_phone": transaction.sender_phone,
                                "recipient_phone": transaction.receiver_phone,
                                "flow": "wallet_to_wallet_payout",
                            },
                        )

                        payout_data = payout_response.get("data") or {}

                        transaction.payout_reference = (
                            payout_data.get("reference")
                            or payout_data.get("external_reference")
                        )
                        transaction.payout_status = (
                            payout_data.get("status")
                            or payout_response.get("status")
                            or "pending"
                        )
                        transaction.payout_response = payout_response
                        transaction.save()

                    except Exception as payout_error:
                        transaction.payout_status = "request_failed"
                        transaction.payout_response = {
                            "error": str(payout_error)
                        }
                        transaction.status = Transaction.STATUS_FAILED
                        transaction.save()

                        return Response(
                            {
                                "success": False,
                                "message": "Payout creation failed",
                                "signature_valid": signature_is_valid,
                            },
                            status=500,
                        )

            elif event_type in ["payment.failed", "payment.expired", "payment.voided"]:
                transaction.status = Transaction.STATUS_FAILED
                transaction.save()

            else:
                transaction.status = Transaction.STATUS_PAYMENT_PENDING
                transaction.save()

            return Response(
                {
                    "success": True,
                    "message": "Payment webhook processed",
                    "signature_valid": signature_is_valid,
                },
                status=200,
            )

        if event_type.startswith("payout."):
            transaction = None

            payout_reference = event.get("reference")
            if payout_reference:
                transaction = Transaction.objects.filter(
                    payout_reference=payout_reference
                ).first()

            if not transaction and metadata.get("transaction_id"):
                transaction = Transaction.objects.filter(
                    id=metadata.get("transaction_id")
                ).first()

            if not transaction:
                return Response(
                    {"success": False, "message": "Payout transaction not found"},
                    status=404,
                )

            transaction.payout_response = event["raw"]
            transaction.payout_status = provider_status
            transaction.provider_name = "snippe"

            if event_type == "payout.completed":
                transaction.status = Transaction.STATUS_COMPLETED
            elif event_type in ["payout.failed", "payout.reversed"]:
                transaction.status = Transaction.STATUS_FAILED
            else:
                transaction.status = Transaction.STATUS_PROCESSING

            transaction.save()

            return Response(
                {
                    "success": True,
                    "message": "Payout webhook processed",
                    "signature_valid": signature_is_valid,
                },
                status=200,
            )

        return Response(
            {
                "success": True,
                "message": "Unhandled webhook event ignored",
                "signature_valid": signature_is_valid,
            },
            status=200,
        )

    except Exception as e:
        return Response(
            {"success": False, "stage": "payment_webhook", "message": str(e)},
            status=500,
        )