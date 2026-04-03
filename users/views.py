from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import UserProfile
from .serializers import UserProfileSerializer
from .azure import create_voice_profile, enroll_voice, verify_voice

# -----------------------------
# ✅ REGISTER USER (Voice Enrollment)
# -----------------------------
@api_view(['POST'])
def register_voice(request):
    name = request.data.get('name')
    phone = request.data.get('phone')
    audio_file = request.FILES.get('voice')

    if not all([name, phone, audio_file]):
        return Response({"error": "Name, phone, and voice are required"})

    if UserProfile.objects.filter(phone=phone).exists():
        return Response({"error": "Phone already registered"})

    # Create local user first
    user = UserProfile.objects.create(name=name, phone=phone, voice_sample=audio_file)

    # 1️⃣ Create Azure voice profile
    profile = create_voice_profile()
    if 'error' in profile:
        user.delete()
        return Response({"error": "Azure profile creation failed", "details": profile['error']})

    profile_id = profile['identificationProfileId']
    user.voice_profile_id = profile_id
    user.save()

    # 2️⃣ Enroll voice
    enroll_result = enroll_voice(profile_id, audio_file)
    if 'error' in enroll_result:
        user.delete()
        return Response({"error": "Voice enrollment failed", "details": enroll_result['error']})

    return Response({
        "message": "User registered successfully",
        "user": UserProfileSerializer(user).data
    })


# -----------------------------
# ✅ LOGIN (Voice Authentication)
# -----------------------------
@api_view(['POST'])
def login_voice(request):
    phone = request.data.get('phone')
    audio_file = request.FILES.get('voice')

    if not all([phone, audio_file]):
        return Response({"error": "Phone and voice required"})

    try:
        user = UserProfile.objects.get(phone=phone)
    except UserProfile.DoesNotExist:
        return Response({"error": "User not found"})

    # Azure verification
    result = verify_voice(user.voice_profile_id, audio_file)
    if 'error' in result:
        return Response({"error": "Voice verification failed", "details": result['error']})

    if result.get("identifiedProfileId") == user.voice_profile_id:
        return Response({
            "message": f"Welcome {user.name}",
            "user": UserProfileSerializer(user).data
        })
    else:
        return Response({"error": "Voice not recognized"})


# -----------------------------
# ✅ VOICE + TRANSACTION
# -----------------------------
@api_view(['POST'])
def voice_transaction(request):
    sender_phone = request.data.get('phone')
    receiver_phone = request.data.get('receiver_phone')
    amount = request.data.get('amount')
    audio_file = request.FILES.get('voice')

    if not all([sender_phone, receiver_phone, amount, audio_file]):
        return Response({"error": "All fields required"})

    try:
        sender = UserProfile.objects.get(phone=sender_phone)
        receiver = UserProfile.objects.get(phone=receiver_phone)
    except UserProfile.DoesNotExist:
        return Response({"error": "User not found"})

    # Verify sender's voice
    result = verify_voice(sender.voice_profile_id, audio_file)
    if 'error' in result:
        return Response({"error": "Voice verification failed", "details": result['error']})

    if result.get("identifiedProfileId") != sender.voice_profile_id:
        return Response({"error": "Voice not recognized"})

    # Perform transaction
    try:
        amount = int(amount)
    except ValueError:
        return Response({"error": "Invalid amount"})

    if sender.balance < amount:
        return Response({"error": "Insufficient balance"})

    sender.balance -= amount
    receiver.balance += amount

    sender.save()
    receiver.save()

    return Response({
        "message": "Transaction successful",
        "sender_balance": sender.balance,
        "receiver_balance": receiver.balance
    })