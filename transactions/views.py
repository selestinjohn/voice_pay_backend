import re
import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import UserProfile, Transaction
from .clickpesa_service import ClickPesaService


# =========================
# VOICE PARSER
# =========================
def parse_command(text):
    text = text.lower().strip()

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


# =========================
# REGISTER
# =========================
@api_view(["POST"])
def register_user(request):
    name = request.data.get("name")
    phone = request.data.get("phone")
    passphrase = request.data.get("passphrase")

    if not name or not phone or not passphrase:
        return Response({"success": False, "message": "All fields required"}, status=400)

    if UserProfile.objects.filter(phone=phone).exists():
        return Response({"success": False, "message": "Phone already exists"}, status=400)

    user = UserProfile.objects.create(
        name=name,
        phone=phone,
        passphrase=passphrase,
    )

    return Response({
        "success": True,
        "message": "Registration successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "balance": user.balance,
        }
    })


# =========================
# LOGIN
# =========================
@api_view(["POST"])
def login_user(request):
    phone = request.data.get("phone")
    passphrase = request.data.get("passphrase")

    if not phone or not passphrase:
        return Response({"success": False, "message": "All fields required"}, status=400)

    try:
        user = UserProfile.objects.get(phone=phone)
    except UserProfile.DoesNotExist:
        return Response({"success": False, "message": "User not found"}, status=404)

    if user.passphrase != passphrase:
        return Response({"success": False, "message": "Invalid passphrase"}, status=400)

    return Response({
        "success": True,
        "message": f"Welcome {user.name}",
        "user": {
            "id": user.id,
            "name": user.name,
            "phone": user.phone,
            "balance": user.balance,
        }
    })


# =========================
# CHECK BALANCE
# =========================
@api_view(["POST"])
def check_balance(request):
    phone = request.data.get("phone")

    if not phone:
        return Response({"success": False, "message": "Phone required"}, status=400)

    try:
        user = UserProfile.objects.get(phone=phone)
    except UserProfile.DoesNotExist:
        return Response({"success": False, "message": "User not found"}, status=404)

    return Response({
        "success": True,
        "balance": user.balance,
        "message": f"Your balance is {user.balance} TZS",
    })


# =========================
# SEND MONEY (CLICKPESA)
# =========================
@api_view(["POST"])
def send_money(request):
    sender_phone = request.data.get("sender_phone")
    receiver_phone = request.data.get("receiver_phone")
    amount = request.data.get("amount")

    if not all([sender_phone, receiver_phone, amount]):
        return Response({"success": False, "message": "All fields required"}, status=400)

    try:
        amount = int(amount)
    except:
        return Response({"success": False, "message": "Invalid amount"}, status=400)

    if amount <= 0:
        return Response({"success": False, "message": "Amount must be greater than zero"}, status=400)

    try:
        sender = UserProfile.objects.get(phone=sender_phone)
    except UserProfile.DoesNotExist:
        return Response({"success": False, "message": "Sender not found"}, status=404)

    if sender.balance < amount:
        return Response({"success": False, "message": "Insufficient balance"}, status=400)

    # Convert number → ClickPesa format
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
        preview = ClickPesaService.preview_mobile_money_payout(
            phone_number=clickpesa_phone,
            amount=amount,
            order_reference=order_reference,
        )

        payout = ClickPesaService.create_mobile_money_payout(
            phone_number=clickpesa_phone,
            amount=amount,
            order_reference=order_reference,
        )

        transaction.status = "processing"
        transaction.clickpesa_status = payout.get("status", "PROCESSING")
        transaction.clickpesa_response = {
            "preview": preview,
            "payout": payout,
        }
        transaction.save()

        return Response({
            "success": True,
            "message": "Payment initiated",
            "order_reference": order_reference,
        })

    except Exception as e:
        transaction.status = "failed"
        transaction.clickpesa_status = "FAILED"
        transaction.clickpesa_response = {"error": str(e)}
        transaction.save()

        return Response({"success": False, "message": str(e)}, status=400)


# =========================
# QUERY STATUS
# =========================
@api_view(["GET"])
def query_payout_status(request, order_reference):
    try:
        transaction = Transaction.objects.get(clickpesa_order_reference=order_reference)
    except Transaction.DoesNotExist:
        return Response({"success": False, "message": "Transaction not found"}, status=404)

    try:
        result = ClickPesaService.query_payout_status(order_reference)

        transaction.clickpesa_status = result.get("status", transaction.clickpesa_status)
        transaction.clickpesa_response = result

        if transaction.clickpesa_status == "SUCCESS":
            transaction.status = "completed"
        elif transaction.clickpesa_status in ["FAILED", "CANCELLED", "REJECTED"]:
            transaction.status = "failed"

        transaction.save()

        return Response({
            "success": True,
            "status": transaction.clickpesa_status,
            "data": result,
        })

    except Exception as e:
        return Response({"success": False, "message": str(e)}, status=400)


# =========================
# WEBHOOK (IMPORTANT)
# =========================
@api_view(["POST"])
def clickpesa_webhook(request):
    try:
        data = request.data
        print("Webhook received:", data)

        order_reference = data.get("orderReference")
        status = data.get("status")

        if not order_reference:
            return Response({"success": False, "message": "Missing orderReference"}, status=400)

        try:
            transaction = Transaction.objects.get(
                clickpesa_order_reference=order_reference
            )
        except Transaction.DoesNotExist:
            return Response({"success": False, "message": "Transaction not found"}, status=404)

        transaction.clickpesa_status = status
        transaction.clickpesa_response = data

        if status == "SUCCESS":
            if transaction.status != "completed":
                sender = UserProfile.objects.get(phone=transaction.sender_phone)

                if sender.balance >= transaction.amount:
                    sender.balance -= transaction.amount
                    sender.save()

                    transaction.status = "completed"
                else:
                    transaction.status = "failed"

        elif status in ["FAILED", "CANCELLED", "REJECTED"]:
            transaction.status = "failed"

        else:
            transaction.status = "processing"

        transaction.save()

        return Response({"success": True, "message": "Webhook processed"})

    except Exception as e:
        return Response({"success": False, "message": str(e)}, status=400)


# =========================
# VOICE ENTRY POINT
# =========================
@api_view(["POST"])
def process_voice(request):
    text = request.data.get("text")
    user_phone = request.data.get("user_phone")

    if not text or not user_phone:
        return Response({"success": False, "message": "Missing input"}, status=400)

    parsed = parse_command(text)

    if parsed["action"] == "check_balance":
        request._full_data = {"phone": user_phone}
        return check_balance(request)

    if parsed["action"] == "send_money":
        request._full_data = {
            "sender_phone": user_phone,
            "receiver_phone": parsed["phone"],
            "amount": parsed["amount"],
        }
        return send_money(request)

    return Response({"success": False, "message": "Command not recognized"}, status=400)