import re
import uuid
import json
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import UserProfile, Transaction


def get_request_data(request):
    try:
        data = request.data
        if data:
            return data
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
        action = "send_money"
    else:
        action = "unknown"

    amount_match = re.findall(r"\d+", text)
    amount = int(amount_match[0]) if amount_match else None

    phone_match = re.findall(r"0\d{9}", text)
    phone = phone_match[0] if phone_match else None

    return {
        "action": action,
        "amount": amount,
        "phone": phone,
    }


@api_view(["POST"])
def register_user(request):
    try:
        data = get_request_data(request)

        name = data.get("name")
        phone = data.get("phone")
        passphrase = data.get("passphrase")

        if not name or not phone or not passphrase:
            raw_body = ""
            try:
                raw_body = request.body.decode("utf-8")
            except Exception:
                raw_body = "could not decode body"

            return Response(
                {
                    "success": False,
                    "stage": "validation",
                    "message": "All fields are required",
                    "received_data": data,
                    "raw_body": raw_body,
                    "content_type": getattr(request, "content_type", ""),
                },
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
            status=200,
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
                {
                    "success": False,
                    "stage": "validation",
                    "message": "All fields are required",
                    "received_data": data,
                },
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
def send_money(request):
    try:
        data = get_request_data(request)

        sender_phone = data.get("sender_phone")
        receiver_phone = data.get("receiver_phone")
        amount = data.get("amount")

        if not all([sender_phone, receiver_phone, amount]):
            return Response(
                {
                    "success": False,
                    "stage": "validation",
                    "message": "All fields are required",
                    "received_data": data,
                },
                status=400,
            )

        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return Response(
                {
                    "success": False,
                    "stage": "validation",
                    "message": "Invalid amount",
                },
                status=400,
            )

        if amount <= 0:
            return Response(
                {
                    "success": False,
                    "stage": "validation",
                    "message": "Amount must be greater than zero",
                },
                status=400,
            )

        try:
            sender = UserProfile.objects.get(phone=sender_phone)
        except UserProfile.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "stage": "sender_lookup",
                    "message": "Sender not found",
                },
                status=404,
            )

        if sender.balance < amount:
            return Response(
                {
                    "success": False,
                    "stage": "balance_check",
                    "message": "Insufficient balance",
                },
                status=400,
            )

        if receiver_phone.startswith("0") and len(receiver_phone) == 10:
            clickpesa_phone = "255" + receiver_phone[1:]
        else:
            clickpesa_phone = receiver_phone

        order_reference = f"VP-{uuid.uuid4().hex[:12].upper()}"

        transaction = Transaction.objects.create(
            sender_phone=sender_phone,
            receiver_phone=receiver_phone,
            amount=amount,
            action="send_money",
            status="pending",
            clickpesa_order_reference=order_reference,
        )

        try:
            from .clickpesa_service import ClickPesaService
        except Exception as e:
            transaction.status = "failed"
            transaction.clickpesa_status = "IMPORT_FAILED"
            transaction.clickpesa_response = {"error": str(e)}
            transaction.save()

            return Response(
                {
                    "success": False,
                    "stage": "import_clickpesa_service",
                    "message": str(e),
                },
                status=500,
            )

        try:
            preview = ClickPesaService.preview_mobile_money_payout(
                phone_number=clickpesa_phone,
                amount=amount,
                order_reference=order_reference,
            )
        except Exception as e:
            transaction.status = "failed"
            transaction.clickpesa_status = "PREVIEW_FAILED"
            transaction.clickpesa_response = {"error": str(e)}
            transaction.save()

            return Response(
                {
                    "success": False,
                    "stage": "preview_mobile_money_payout",
                    "message": str(e),
                    "order_reference": order_reference,
                },
                status=400,
            )

        try:
            payout = ClickPesaService.create_mobile_money_payout(
                phone_number=clickpesa_phone,
                amount=amount,
                order_reference=order_reference,
            )
        except Exception as e:
            transaction.status = "failed"
            transaction.clickpesa_status = "CREATE_PAYOUT_FAILED"
            transaction.clickpesa_response = {
                "preview": preview,
                "error": str(e),
            }
            transaction.save()

            return Response(
                {
                    "success": False,
                    "stage": "create_mobile_money_payout",
                    "message": str(e),
                    "order_reference": order_reference,
                    "preview": preview,
                },
                status=400,
            )

        transaction.status = "processing"
        transaction.clickpesa_status = payout.get("status", "PROCESSING")
        transaction.clickpesa_response = {
            "preview": preview,
            "payout": payout,
        }
        transaction.save()

        return Response(
            {
                "success": True,
                "message": "Payment initiated",
                "order_reference": order_reference,
                "transaction_id": transaction.id,
                "clickpesa_status": transaction.clickpesa_status,
                "preview": preview,
                "payout": payout,
            },
            status=200,
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "stage": "outer_exception",
                "message": str(e),
            },
            status=500,
        )


@api_view(["GET"])
def query_payout_status(request, order_reference):
    try:
        try:
            transaction = Transaction.objects.get(
                clickpesa_order_reference=order_reference
            )
        except Transaction.DoesNotExist:
            return Response(
                {"success": False, "message": "Transaction not found"},
                status=404,
            )

        try:
            from .clickpesa_service import ClickPesaService
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "stage": "import_clickpesa_service",
                    "message": str(e),
                },
                status=500,
            )

        try:
            result = ClickPesaService.query_payout_status(order_reference)
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "stage": "query_payout_status",
                    "message": str(e),
                    "order_reference": order_reference,
                },
                status=400,
            )

        transaction.clickpesa_status = result.get("status", transaction.clickpesa_status)
        transaction.clickpesa_response = result

        if transaction.clickpesa_status == "SUCCESS":
            transaction.status = "completed"
        elif transaction.clickpesa_status in ["FAILED", "CANCELLED", "REJECTED"]:
            transaction.status = "failed"
        else:
            transaction.status = "processing"

        transaction.save()

        return Response(
            {
                "success": True,
                "status": transaction.clickpesa_status,
                "data": result,
            },
            status=200,
        )

    except Exception as e:
        return Response(
            {"success": False, "stage": "query_status_outer_exception", "message": str(e)},
            status=500,
        )


@api_view(["GET", "POST"])
def clickpesa_webhook(request):
    if request.method == "GET":
        return Response(
            {
                "success": True,
                "message": "Webhook route is working",
            },
            status=200,
        )

    try:
        data = get_request_data(request)
        order_reference = data.get("orderReference")
        payment_status = data.get("status")

        if not order_reference:
            return Response(
                {"success": False, "message": "Missing orderReference"},
                status=400,
            )

        transaction = Transaction.objects.filter(
            clickpesa_order_reference=order_reference
        ).first()

        if not transaction:
            return Response(
                {"success": False, "message": "Transaction not found"},
                status=404,
            )

        transaction.clickpesa_status = payment_status
        transaction.clickpesa_response = data

        if payment_status == "SUCCESS":
            if transaction.status != "completed":
                sender = UserProfile.objects.filter(phone=transaction.sender_phone).first()

                if not sender:
                    transaction.status = "failed"
                    transaction.clickpesa_status = "SENDER_NOT_FOUND"
                elif sender.balance >= transaction.amount:
                    sender.balance -= transaction.amount
                    sender.save()
                    transaction.status = "completed"
                else:
                    transaction.status = "failed"
                    transaction.clickpesa_status = "INSUFFICIENT_BALANCE"

        elif payment_status in ["FAILED", "CANCELLED", "REJECTED"]:
            transaction.status = "failed"
        else:
            transaction.status = "processing"

        transaction.save()

        return Response(
            {
                "success": True,
                "message": "Webhook processed",
            },
            status=200,
        )

    except Exception as e:
        return Response(
            {"success": False, "stage": "clickpesa_webhook", "message": str(e)},
            status=500,
        )


@api_view(["POST"])
def process_voice(request):
    try:
        data = get_request_data(request)

        text = data.get("text")
        user_phone = data.get("user_phone")

        if not text:
            return Response(
                {"success": False, "message": "No text provided"},
                status=400,
            )

        if not user_phone:
            return Response(
                {"success": False, "message": "User phone is required"},
                status=400,
            )

        parsed = parse_command(text)

        if parsed.get("action") == "check_balance":
            class FakeRequest:
                pass

            fake_request = FakeRequest()
            fake_request.data = {"phone": user_phone}
            fake_request.body = b""
            return check_balance(fake_request)

        if parsed.get("action") == "send_money":
            if not parsed.get("amount"):
                return Response(
                    {"success": False, "message": "Specify amount"},
                    status=400,
                )

            if not parsed.get("phone"):
                return Response(
                    {"success": False, "message": "Provide phone number"},
                    status=400,
                )

            class FakeRequest:
                pass

            fake_request = FakeRequest()
            fake_request.data = {
                "sender_phone": user_phone,
                "receiver_phone": parsed["phone"],
                "amount": parsed["amount"],
            }
            fake_request.body = b""
            return send_money(fake_request)

        return Response(
            {"success": False, "message": "Command not recognized"},
            status=400,
        )

    except Exception as e:
        return Response(
            {"success": False, "stage": "process_voice", "message": str(e)},
            status=500,
        )