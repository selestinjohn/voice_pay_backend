from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
import tempfile

encoder = VoiceEncoder()


# ✅ Generate embedding from uploaded audio file
def get_embedding(audio_file):
    with tempfile.NamedTemporaryFile(delete=False) as temp_audio:
        for chunk in audio_file.chunks():
            temp_audio.write(chunk)

        temp_audio_path = temp_audio.name

    wav = preprocess_wav(temp_audio_path)
    embedding = encoder.embed_utterance(wav)

    return embedding


# ✅ Compare two embeddings
def compare_embeddings(emb1, emb2):
    emb1 = np.array(emb1)
    emb2 = np.array(emb2)

    similarity = np.dot(emb1, emb2) / (
        np.linalg.norm(emb1) * np.linalg.norm(emb2)
    )

    return similarity