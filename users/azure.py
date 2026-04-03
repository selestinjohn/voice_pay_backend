import requests

# -----------------------------
# 🔹 Azure Config
# -----------------------------
AZURE_ENDPOINT = "https://<YOUR_REGION>.api.cognitive.microsoft.com/spid/v1.0"
AZURE_KEY = "<YOUR_API_KEY>"

HEADERS = {"Ocp-Apim-Subscription-Key": AZURE_KEY}

# -----------------------------
# 🔹 Create new voice profile
# -----------------------------
def create_voice_profile(locale="en-us", enrollment_time=30):
    """
    Create a text-independent Azure speaker identification profile.
    """
    payload = {
        "locale": locale,
        "enrollmentSpeechTime": enrollment_time
    }

    response = requests.post(
        f"{AZURE_ENDPOINT}/identificationProfiles",
        headers=HEADERS,
        json=payload
    )

    if response.status_code in [200, 201]:
        return response.json()  # returns {"identificationProfileId": "..."}
    else:
        return {"error": response.text}

# -----------------------------
# 🔹 Enroll voice for a profile
# -----------------------------
def enroll_voice(profile_id, audio_file):
    """
    Enroll a voice sample to a given Azure profile.
    audio_file: Django UploadedFile
    """
    files = {"file": (audio_file.name, audio_file, "audio/wav")}
    response = requests.post(
        f"{AZURE_ENDPOINT}/identificationProfiles/{profile_id}/enroll?shortAudio=true",
        headers=HEADERS,
        files=files
    )

    if response.status_code in [200, 201, 202]:
        return response.json() if response.content else {"status": "Enrolling"}
    else:
        return {"error": response.text}

# -----------------------------
# 🔹 Verify / Identify voice
# -----------------------------
def verify_voice(profile_id, audio_file):
    """
    Identify user voice against a profile.
    """
    files = {"file": (audio_file.name, audio_file, "audio/wav")}
    response = requests.post(
        f"{AZURE_ENDPOINT}/identify?identificationProfileIds={profile_id}&shortAudio=true",
        headers=HEADERS,
        files=files
    )

    if response.status_code in [200, 201]:
        return response.json()
    else:
        return {"error": response.text}