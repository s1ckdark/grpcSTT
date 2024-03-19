from dotenv import load_dotenv
import os
import requests
import json
import grpc
import pyaudio
import threading
from obswebsocket import obsws, requests
from google.protobuf.json_format import ParseDict, MessageToDict, Parse
import nest_pb2_grpc
import nest_pb2
from collections import deque
from translate import papago_translate # This is the function we want to use
from StreamSentenceMaker import StreamSentenceProcessor

load_dotenv()
obs_host = "localhost"
obs_port = 4455
obs_password = os.environ.get("OBS_PASSWORD")
papago_id = os.environ.get("PAPAGO_ID")
papago_secret = os.environ.get("PAPAGO_SECRET")
secret_key = os.environ.get("SECRET_KEY")
nest_server_address = "clovaspeech-gw.ncloud.com:50051"
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK_SIZE = 1024

def transcribe_stream(audio, ws):
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK_SIZE)
    print("Recording and transcribing audio...")
    with grpc.secure_channel(nest_server_address, grpc.ssl_channel_credentials()) as channel:
        stub = nest_pb2_grpc.NestServiceStub(channel)
        metadata = (('authorization', f'Bearer {secret_key}'),)

        def request_generator():
            try:
                yield nest_pb2.NestRequest(
                    type=nest_pb2.CONFIG,
                    config=nest_pb2.NestConfig(config='{"transcription":{"language":"ko"}}')
                )
                while True:
                    data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    yield nest_pb2.NestRequest(
                        type=nest_pb2.DATA,
                        data=nest_pb2.NestData(chunk=data, extra_contents='{"seqId": 0, "epFlag": false}')
                    )
            except Exception as e:
                print(f"Error during streaming: {e}")

        try:
            responses = stub.recognize(request_generator(), metadata=metadata)
            processor = StreamSentenceProcessor()
            
            for response in responses:
                msg = ParseDict(MessageToDict(response), nest_pb2.NestResponse())
                caption = json.loads(msg.contents)
                if "transcription" in caption:
                    print("Received response:", caption['transcription']['text'])
                    sentence = processor.process_word(caption)
                    if sentence:
                        print("완성된 문장:", sentence)
                        print("번역된 문장:", papago_translate("ko","en",sentence))
                        ws.call(requests.SetInputSettings(inputName="stt", inputSettings={"text":  sentence}))
                        ws.call(requests.SetInputSettings(inputName="papago_en", inputSettings={"text":  papago_translate("ko","en",sentence)}))
                        # ws.call(requests.SetInputSettings(inputName="papago_jp", inputSettings={"text":  papago_translate("ko","ja",sentence)}))
                    # ws.call(requests.SetInputSettings(inputName="nbp", inputSettings={"text":  caption["transcription"]["text"]}))
                # print("Received response:", msg.contents)
                # ws.call(requests.SetInputSettings(inputName="nbp", inputSettings={"text": caption.text}))
        except grpc.RpcError as e:
            print(f"gRPC error: {e}")
        finally:
            stream.stop_stream()
            stream.close()

def main():
    audio = pyaudio.PyAudio()
    ws = obsws(obs_host, obs_port, obs_password)
    ws.connect()
    transcribe_thread = threading.Thread(target=transcribe_stream, args=(audio, ws))
    transcribe_thread.start()
    transcribe_thread.join()
    ws.disconnect()
    audio.terminate()

if __name__ == "__main__":
    main()
