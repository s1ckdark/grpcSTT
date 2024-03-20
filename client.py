# Import necessary libraries
from dotenv import load_dotenv
import os
import json
import grpc
import pyaudio
import threading
from obswebsocket import obsws, requests  
from google.protobuf.json_format import ParseDict, MessageToDict, Parse
import nest_pb2_grpc
import nest_pb2
from collections import deque
from translate import papago_translate  # Assumes custom function for translation
from StreamSentenceMaker import StreamSentenceProcessor

# Load environment variables from a .env file
load_dotenv()
# OBS (Open Broadcaster Software) connection settings
obs_host = "localhost"
obs_port = 4455
obs_password = os.environ.get("OBS_PASSWORD")
# Naver Papago Translation API credentials
papago_id = os.environ.get("PAPAGO_ID")
papago_secret = os.environ.get("PAPAGO_SECRET")
# Secret key for NEST (Clova Speech-to-Text) API
secret_key = os.environ.get("SECRET_KEY")
# NEST server address
nest_server_address = "clovaspeech-gw.ncloud.com:50051"
# PyAudio settings for audio recording
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_SIZE = 1024

def transcribe_stream(audio, ws):
    # Open an audio stream for recording
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE)
    print("Recording and transcribing audio...")
    # Establish a secure gRPC channel to the NEST server
    with grpc.secure_channel(nest_server_address, grpc.ssl_channel_credentials()) as channel:
        stub = nest_pb2_grpc.NestServiceStub(channel)
        metadata = (('authorization', f'Bearer {secret_key}'),)

        # Generator function to send audio chunks to NEST
        def request_generator():
            try:
                # Send initial configuration request
                yield nest_pb2.NestRequest(
                    type=nest_pb2.CONFIG,
                    config=nest_pb2.NestConfig(config='{"transcription":{"language":"ko"}}')
                )
                # Continuously read and send audio chunks
                while True:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    yield nest_pb2.NestRequest(
                        type=nest_pb2.DATA,
                        data=nest_pb2.NestData(chunk=data, extra_contents='{"seqId": 0, "epFlag": false}')
                    )
            except Exception as e:
                print(f"Error during streaming: {e}")

        # Process responses from NEST
        try:
            responses = stub.recognize(request_generator(), metadata=metadata)
            processor = StreamSentenceProcessor()
            
            for response in responses:
                # Parse the response to get transcription text
                msg = ParseDict(MessageToDict(response), nest_pb2.NestResponse())
                caption = json.loads(msg.contents)
                if "transcription" in caption:
                    print("Received response:", caption['transcription']['text'])
                    sentence = processor.process_word(caption)
                    if sentence:
                        # Process and translate the sentence, then send it to OBS
                        print("완성된 문장:", sentence)
                        print("번역된 문장:", papago_translate("ko","en",sentence))
                        # Update OBS text sources with the translated sentences
                        # obs에 텍스트 소스 업데이트 (번역된 문장) 텍스트 박스에 번역된 문장을 업데이트 inputName은 obs에서 설정한 이름
                        ws.call(requests.SetInputSettings(inputName="stt", inputSettings={"text":  sentence}))
                        ws.call(requests.SetInputSettings(inputName="papago_en", inputSettings={"text":  papago_translate("ko","en",sentence)}))
                        ws.call(requests.SetInputSettings(inputName="papago_jp", inputSettings={"text":  papago_translate("ko","ja",sentence)}))
        except grpc.RpcError as e:
            print(f"gRPC error: {e}")
        finally:
            # Clean up: stop the stream and close it
            stream.stop_stream()
            stream.close()

def main():
    # https://github.com/obsproject/obs-websocket 이 플러그인을 obs에 설치해야합니다.
    # Initialize pyaudio and connect to OBS
    audio = pyaudio.PyAudio()
    ws = obsws(obs_host, obs_port, obs_password)
    ws.connect()
    # Start the transcription in a separate thread
    transcribe_thread = threading.Thread(target=transcribe_stream, args=(audio, ws))
    transcribe_thread.start()
    # Wait for the transcription thread to finish
    transcribe_thread.join()
    # Disconnect from OBS and terminate pyaudio
    ws.disconnect()
    audio.terminate()

# Entry point of the script
if __name__ == "__main__":
    main()
