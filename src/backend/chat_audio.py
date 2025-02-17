import os
from dotenv import load_dotenv
import base64
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))

# STT 함수 (음성 인식)
def STT(audio_data: bytes):
    filename = 'input.mp3'
    with open(filename, "wb") as f:
        f.write(audio_data)

    try:
        with open(filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        return transcript
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        os.remove(filename)

# TTS 함수 (음성 합성)
def TTS(response: str):
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="onyx",
        input=response,
    ) as response:
        filename = "output.mp3"
        response.stream_to_file(filename)

    with open(filename, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()

        audio_html = f"""
            <audio autoplay="True">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
        """
    os.remove(filename)
    return audio_html