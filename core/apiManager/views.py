from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from utils.geminiClient import get_genai_client, config, generate_transcript, call_gemini_api, recommend_movies, format_recommendations_text, synthesize_response



@api_view(['GET'])
def health(request):
	return Response({'status': 'ok'})

#TODO: generate transcript
#TODO: call Gemini API with transcript and recommend movies or chat to determine what to recommend
#TODO: return movie recommendations
#TODO: synthesize response with Gemini API

@api_view(['POST'])
def send_audio(request):
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({'error': 'No audio file provided'}, status=status.HTTP_400_BAD_REQUEST)

    response_text = generate_transcript(audio_file)

    return Response({'response': response_text})
    
