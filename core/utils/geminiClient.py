import os
import google.genai as genai
from google.genai import types

import io
import base64
from pathlib import Path
from pydub import AudioSegment
import traceback

# Global model instance to avoid re-initializing on every request
_gemini_model = None

def get_gemini_model():
    """
    Initializes and returns the Gemini GenerativeModel for live audio.
    This function ensures the model is configured once and reused.
    """
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model, None  # Return model and no error

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "":
        error_msg = "GEMINI_API_KEY environment variable not set or empty. Please set it in your .env file."
        print(f"Error initializing Gemini model: {error_msg}")
        return None, error_msg

    try:
        # Instantiate the new Client API (google.genai.Client) with the API key.
        # The client exposes both sync and async surfaces (client and client.aio).
        client = genai.Client(api_key=api_key)
        _gemini_model = client
        return _gemini_model, None  # Return client and no error
    except Exception as e:
        error_msg = f"Error during Gemini model configuration: {e}"
        print(f"Error initializing Gemini model: {error_msg}")
        return None, error_msg
    
# The previous global `model` and `config` variables are now integrated into `get_gemini_model`.
# The `response_modalities` will be passed directly to `generate_content` if needed for audio output.

def generate_transcript(audio_file):
    """
    Sends an audio file to the Gemini Live Audio API for transcription.
    This function assumes `audio_file` is a file-like object (e.g., Django's UploadedFile).
    It reads the entire audio file content and sends it as a single part.

    Args:
        audio_file: A file-like object containing the audio data.
                    Assumed to be in a format compatible with Gemini (e.g., WAV).

    Returns:
        str: The transcribed text from the audio.
    """
    model, model_err = get_gemini_model()
    if not model:
        return f"Error: Gemini model not initialized. {model_err or ''}"

    # Replace live realtime transcription with a non-live approach.
    try:
        audio_file.seek(0)
        audio = AudioSegment.from_file(audio_file)

        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        wav_bytes = wav_io.read()

        # Prefer uploading the file (if supported) then calling the models API.
        gemini_file = None
        try:
            gemini_file = model.files.upload(file=io.BytesIO(wav_bytes), config=types.UploadFileConfig(mime_type='audio/wav', display_name='upload.wav'))
        except Exception:
            gemini_file = None

        try:
            # Build an inline audio part (Blob) and ask the model to transcribe it.
            audio_blob = types.Blob(data=wav_bytes, mime_type='audio/wav')
            part = types.Part(inline_data=audio_blob)
            content = types.Content(parts=[part], role='user')

            # Call the synchronous models.generate_content method. Use a stable
            # text-model name that supports multimodal inputs; pick a generic
            # 'gemini-2.5' here — adjust if you have a specific model.
            response = model.models.generate_content(
                model='gemini-2.5',
                contents=[content],
                stream=False,
            )

            if response and getattr(response, 'candidates', None):
                for p in response.candidates[0].content.parts:
                    if getattr(p, 'text', None):
                        return p.text
            return 'Could not generate transcript.'
        except Exception as e:
            print(f'Error calling non-live models for transcription: {e}')
            print(traceback.format_exc())
            return f'Error generating transcript: {e}'

    except Exception as e:
        print(f"Error preparing audio for transcription: {e}")
        print(traceback.format_exc())
        return f"Error generating transcript: {e}"

def call_gemini_api(transcript):
    """
    Calls the Gemini API with a given text transcript to get a text response.
    """
    model, model_err = get_gemini_model()
    if not model:
        return f"Error: Gemini model not initialized. {model_err or ''}"

    try:
        response = model.generate_content(
            transcript,
            stream=False, # Get the full response
        )

        if response and response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    return part.text
        return "Could not get a response from Gemini."

    except Exception as e:
        print(f"Error calling Gemini API with transcript: {e}")
        return f"Error interacting with Gemini: {e}"

def recommend_movies(gemini_response):
    # This function would parse Gemini's text response to extract movie recommendations.
    if "recommendations" in gemini_response.lower():
        return f"Based on your request, Gemini recommended: {gemini_response}"
    return f"Gemini's response: {gemini_response}"

def format_recommendations_text(recommendations):
    # This function would take structured recommendations and format them into natural language.
    return f"Here are your formatted recommendations: {recommendations}"

def synthesize_response(gemini_response):
    """
    Synthesizes a text response into audio using Gemini's text-to-speech capabilities.
    This requires `response_modalities=["AUDIO"]` in the `generate_content` call.
    """
    model, model_err = get_gemini_model()
    if not model:
        print(f"synthesize_response: Gemini model not initialized. {model_err or ''}")
        return None  # Or raise an error

    try:
        # To get audio output, we need to specify response_modalities=["AUDIO"]
        response = model.generate_content(
            gemini_response,
            stream=False,  # Can be streamed for longer audio
            generation_config=types.GenerateContentConfig(response_modalities=["AUDIO"]),
        )

        # The audio content will be in `response.candidates[0].content.parts`
        audio_data_chunks = []
        if response and getattr(response, 'candidates', None):
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'audio_data'):
                    audio_data_chunks.append(part.audio_data)
        
        # Concatenate audio chunks if multiple parts are returned
        if audio_data_chunks:
            # The audio_data is typically raw PCM or a specific format.
            # You might need to wrap it in a WAV header or similar for playback.
            # For simplicity, let's return the raw concatenated bytes.
            return b"".join(audio_data_chunks)
        return None

    except Exception as e:
        print(f"Error synthesizing response: {e}")
        return None

def process_audio_and_get_audio_response(audio_file):
    """
    Sends an audio file to the Gemini API and gets a synthesized audio response
    in a single call.

    Args:
        audio_file: A file-like object containing the user's audio.

    Returns:
        bytes: The synthesized audio data from Gemini, or None on error.
        str: The intermediate text response from Gemini, or an error message.
    """
    model, model_init_error = get_gemini_model()  # Unpack the tuple
    if not model:
        # If model initialization failed, return the specific error message from get_gemini_model
        return None, f"Error: Gemini model not initialized. {model_init_error}"

    try:
        audio_file.seek(0)
        audio = AudioSegment.from_file(audio_file)
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)

        wav_bytes = wav_io.read()

        async def _live_unified(async_client, model_name, audio_bytes):
            text_resp = None
            audio_resp_chunks: list[bytes] = []
            async with async_client.live.connect(
                model=model_name,
                # Request AUDIO only to avoid websocket frame errors for
                # models that don't support TEXT in response_modalities
                config={"response_modalities": ["AUDIO"]},
            ) as session:
                try:
                    # Convert incoming WAV bytes to 16kHz mono 16-bit PCM for live websocket
                    try:
                        seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
                        seg = seg.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                        pcm_bytes = seg.raw_data
                        audio_blob = types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000")
                    except Exception as conv_err:
                        # If conversion fails for any reason, fall back to sending the original WAV bytes
                        print(f"PCM conversion failed, falling back to WAV: {conv_err}")
                        print(traceback.format_exc())
                        audio_blob = types.Blob(data=audio_bytes, mime_type="audio/wav")

                    await session.send_realtime_input(audio=audio_blob)
                except Exception as e:
                    print(f"Error sending realtime audio in unified flow: {e}")
                    print(traceback.format_exc())
                    raise

                async for msg in session.receive():
                    # message may contain text
                    if getattr(msg, 'text', None):
                        text_resp = msg.text
                    # attempt to extract audio bytes from server_content or other fields
                    server_content = getattr(msg, 'server_content', None)
                    if server_content:
                        # server_content may include parts with audio_data
                        parts = getattr(server_content, 'parts', None) or []
                        for part in parts:
                            if hasattr(part, 'audio_data') and part.audio_data:
                                audio_resp_chunks.append(part.audio_data)

                # return concatenated audio and text
                return (b"".join(audio_resp_chunks) if audio_resp_chunks else None, text_resp)

        result = __import__('asyncio').run(
            _live_unified(model.aio, model_name="gemini-2.5-flash-native-audio-preview-09-2025", audio_bytes=wav_bytes)
        )

        # If the live session did not return any text (we requested AUDIO only),
        # fall back to the non-live transcription path using the models API.
        audio_resp, text_resp = result
        if not text_resp:
            try:
                # generate_transcript expects a file-like object; pass wav bytes
                transcript = generate_transcript(io.BytesIO(wav_bytes))
                text_resp = transcript
            except Exception:
                text_resp = None

        return (audio_resp, text_resp)

    except Exception as e:
        print(f"Error in unified audio processing: {e}")
        print(traceback.format_exc())
        return None, f"Error processing audio: {e}"
