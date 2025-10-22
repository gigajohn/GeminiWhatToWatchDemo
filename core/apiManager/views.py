from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
import os

# Import the necessary functions from your Gemini client utility
from utils.geminiClient import process_audio_and_get_audio_response

@api_view(['GET'])
def health(request):
	return Response({'status': 'ok'})

#TODO: generate transcript
#TODO: call Gemini API with transcript and recommend movies or chat to determine what to recommend
#TODO: return movie recommendations
#TODO: synthesize response with Gemini API

@api_view(['POST'])
def send_audio(request):
    print("--- send_audio view entered ---")
    """
    Connects to Gemini Live API to process the incoming audio
    """
    # With DRF's default parsers for multipart/form-data, the file will be in request.FILES
    audio_file = request.FILES.get('audio')

    if not audio_file:
        return Response({'error': 'No audio file provided. Ensure the request is multipart/form-data and includes a field named "audio".'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Save incoming uploaded file to MEDIA_ROOT/uploads with a unique filename
        try:
            uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S_%f')
            incoming_filename = f"upload_{timestamp}_{audio_file.name}"
            incoming_path = os.path.join(uploads_dir, incoming_filename)
            with open(incoming_path, 'wb') as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)
            print(f"Saved incoming audio to {incoming_path}")
        except Exception as save_ex:
            print(f"Warning: failed to save incoming audio: {save_ex}")

        # 1. Process the audio and get an audio response in a single call
        audio_response_data, gemini_text_response = process_audio_and_get_audio_response(audio_file)
    except Exception as e:
        # Log the full exception and return it to the caller for debugging
        print(f"Exception while processing audio: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # You can optionally log or use the intermediate text response
    print(f"Gemini's text response: {gemini_text_response}")

    if not audio_response_data:
        error_message = f"Failed to get audio response from Gemini. Details: {gemini_text_response}"
        return Response({'error': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Save outgoing response audio to MEDIA_ROOT/responses with a unique filename
    try:
        responses_dir = os.path.join(settings.MEDIA_ROOT, 'responses')
        os.makedirs(responses_dir, exist_ok=True)
        resp_timestamp = timezone.now().strftime('%Y%m%d_%H%M%S_%f')
        # attempt to use .mp3 extension; adjust if Gemini returns PCM/WAV
        outgoing_filename = f"response_{resp_timestamp}.mp3"
        outgoing_path = os.path.join(responses_dir, outgoing_filename)
        with open(outgoing_path, 'wb') as outf:
            outf.write(audio_response_data)
        print(f"Saved outgoing audio to {outgoing_path}")
    except Exception as save_ex:
        print(f"Warning: failed to save outgoing audio: {save_ex}")

    # 2. Return the synthesized audio as the response
    # The Gemini API typically returns audio as 'audio/mpeg'
    return HttpResponse(audio_response_data, content_type='audio/mpeg')
    
