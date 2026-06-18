from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from pydub import AudioSegment
from unittest.mock import patch
import io

class VoiceToTextTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('text_to_voice')

    def test_voice_to_text_invalid_format(self):
        # Test that unsupported files (e.g. .txt) are rejected
        dummy_file = SimpleUploadedFile("test.txt", b"some text content", content_type="text/plain")
        response = self.client.post(self.url, {
            'action': 'voice_to_text',
            'input_language': 'en',
            'output_language': 'en',
            'audio': dummy_file
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Only .wav, .mp3, and .ogg files are supported.", response.content.decode('utf-8'))

    def test_voice_to_text_wav(self):
        # Generate a small silent wav file
        audio = AudioSegment.silent(duration=500)
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        
        uploaded_file = SimpleUploadedFile("test.wav", wav_io.read(), content_type="audio/wav")
        
        response = self.client.post(self.url, {
            'action': 'voice_to_text',
            'input_language': 'en',
            'output_language': 'en',
            'audio': uploaded_file
        })
        self.assertEqual(response.status_code, 200)
        # Should reach Google Speech Recognition, fail to understand silent audio, and return error
        self.assertIn("Could not understand audio.", response.content.decode('utf-8'))

    def test_voice_to_text_mp3(self):
        # Generate a small silent mp3 file
        audio = AudioSegment.silent(duration=500)
        mp3_io = io.BytesIO()
        audio.export(mp3_io, format="mp3")
        mp3_io.seek(0)
        
        uploaded_file = SimpleUploadedFile("test.mp3", mp3_io.read(), content_type="audio/mpeg")
        
        response = self.client.post(self.url, {
            'action': 'voice_to_text',
            'input_language': 'en',
            'output_language': 'en',
            'audio': uploaded_file
        })
        self.assertEqual(response.status_code, 200)
        # Should be successfully converted, read by speech recognizer, and fail on silence
        self.assertIn("Could not understand audio.", response.content.decode('utf-8'))

    def test_voice_to_text_ogg(self):
        # Generate a small silent ogg file
        audio = AudioSegment.silent(duration=500)
        ogg_io = io.BytesIO()
        audio.export(ogg_io, format="ogg")
        ogg_io.seek(0)
        
        uploaded_file = SimpleUploadedFile("test.ogg", ogg_io.read(), content_type="audio/ogg")
        
        response = self.client.post(self.url, {
            'action': 'voice_to_text',
            'input_language': 'en',
            'output_language': 'en',
            'audio': uploaded_file
        })
        self.assertEqual(response.status_code, 200)
        # Should be successfully converted, read by speech recognizer, and fail on silence
        self.assertIn("Could not understand audio.", response.content.decode('utf-8'))

    @patch('speech_recognition.Recognizer.recognize_google')
    def test_voice_to_text_chunking(self, mock_recognize):
        # We have a 70-second audio (which is split into 3 chunks: 30s, 30s, 10s)
        # We will mock the responses for each chunk
        mock_recognize.side_effect = ["hello", "world", "this is testing"]
        
        audio = AudioSegment.silent(duration=70000)
        mp3_io = io.BytesIO()
        audio.export(mp3_io, format="mp3")
        mp3_io.seek(0)
        
        uploaded_file = SimpleUploadedFile("test.mp3", mp3_io.read(), content_type="audio/mpeg")
        
        response = self.client.post(self.url, {
            'action': 'voice_to_text',
            'input_language': 'en',
            'output_language': 'en',
            'audio': uploaded_file
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), "hello world this is testing")
        self.assertEqual(mock_recognize.call_count, 3)
