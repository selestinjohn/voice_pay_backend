from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def register_user(request):
    return Response({"success": True, "message": "register route working"})


@api_view(["GET"])
def login_user(request):
    return Response({"success": True, "message": "login route working"})


@api_view(["GET"])
def check_balance(request):
    return Response({"success": True, "message": "check balance route working"})


@api_view(["GET"])
def send_money(request):
    return Response({"success": True, "message": "send money route working"})


@api_view(["GET"])
def process_voice(request):
    return Response({"success": True, "message": "process voice route working"})


@api_view(["GET"])
def query_payout_status(request, order_reference):
    return Response({
        "success": True,
        "message": "query payout status route working",
        "order_reference": order_reference,
    })


@api_view(["GET"])
def clickpesa_webhook(request):
    return Response({
        "success": True,
        "message": "Webhook route is working",
    })