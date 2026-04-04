import re
import uuid
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import UserProfile, Transaction


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
    name = request.data.get("name")
    phone = request.data.get("phone")
    passphrase = request.data.get("passphrase")

    if not name or not phone or not passphrase:
        return Response({"success": False, "message": "All fields are required"}, status=400)

    if UserProfile.objects.filter(phone=phone).exists():
        return Response({"success": False, "message": "Phone already exists"}, status=400)

    user = UserProfile.objects.create(name=name, phone=phone, passphrase=passphrase)

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


@api_view(["POST"])
def login_user(request):
    phone = request.data.get("phone")
    passphrase = request.data.get("passphrase")

    if not phone or not passphrase:
        return Response({"success": False, "message": "All fields are required"}, status=400)

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


@api_view(["POST"])
def check_balance(request):
    phone = request.data.get("phone")

    if not phone:
        return Response({"success": False, "message": "Phone is required"}, status=400)

    try:
        user = UserProfile.objects.get(phone=phone)
    except UserProfile.DoesNotExist:
        return Response({"success": False, "message": "User not found"}, status=404)

    return Response({
        "success": True,
        "balance": user.balance,
        "message": f"Your balance is {user.balance} TZS",
    })


@api_view(["POST"])
def send_money(request):
    return Response({
        "success": False,
        "message": "send_money temporarily disabled for debugging"
    }, status=503)


@api_view(["GET"])
def query_payout_status(request, order_reference):
    return Response({
        "success": False,
        "message": "query_payout_status temporarily disabled for debugging",
        "order_reference": order_reference
    }, status=503)


@api_view(["GET", "POST"])
def clickpesa_webhook(request):
    if request.method == "GET":
        return Response({
            "success": True,
            "message": "Webhook route is working"
        }, status=200)

    return Response({
        "success": True,
        "message": "POST received"
    }, status=200)


@api_view(["POST"])
def process_voice(request):
    text = request.data.get("text")
    user_phone = request.data.get("user_phone")

    if not text:
        return Response({"success": False, "message": "No text provided"}, status=400)

    if not user_phone:
        return Response({"success": False, "message": "User phone is required"}, status=400)

    parsed = parse_command(text)

    if parsed.get("action") == "check_balance":
        request._full_data = {"phone": user_phone}
        return check_balance(request)

    if parsed.get("action") == "send_money":
        return Response({
            "success": False,
            "message": "send_money temporarily disabled for debugging"
        }, status=503)

    return Response({"success": False, "message": "Command not recognized"}, status=400)