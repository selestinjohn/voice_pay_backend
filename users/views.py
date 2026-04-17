from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import UserProfile
from .serializers import UserProfileSerializer


@api_view(["POST"])
def register_voice(request):
    name = request.data.get("name")
    phone = request.data.get("phone")
    passphrase = request.data.get("passphrase")

    if not all([name, phone, passphrase]):
        return Response(
            {
                "success": False,
                "message": "Name, phone, and passphrase are required",
            },
            status=400,
        )

    if UserProfile.objects.filter(phone=phone).exists():
        return Response(
            {
                "success": False,
                "message": "Phone already registered",
            },
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
            "message": "User registered successfully",
            "user": UserProfileSerializer(user).data,
        },
        status=201,
    )


@api_view(["POST"])
def login_voice(request):
    phone = request.data.get("phone")
    passphrase = request.data.get("passphrase")

    if not all([phone, passphrase]):
        return Response(
            {
                "success": False,
                "message": "Phone and passphrase are required",
            },
            status=400,
        )

    try:
        user = UserProfile.objects.get(phone=phone)
    except UserProfile.DoesNotExist:
        return Response(
            {
                "success": False,
                "message": "User not found",
            },
            status=404,
        )

    if user.passphrase != passphrase:
        return Response(
            {
                "success": False,
                "message": "Invalid passphrase",
            },
            status=400,
        )

    return Response(
        {
            "success": True,
            "message": f"Welcome {user.name}",
            "user": UserProfileSerializer(user).data,
        },
        status=200,
    )