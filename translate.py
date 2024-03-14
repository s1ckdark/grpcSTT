import requests
import json
from dotenv import load_dotenv
import os
import sys

load_dotenv()
papago_id = os.environ.get("PAPAGO_ID")
papago_secret = os.environ.get("PAPAGO_SECRET")

def papago_translate(source, target, text):
    if len(text) > 0:
        data = {
            "source": source,
            "target": target,
            "text": text
        }
        url = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"
        headers = {
            "X-NCP-APIGW-API-KEY-ID": papago_id,
            "X-NCP-APIGW-API-KEY": papago_secret
        }
        response = requests.post(url, data=data, headers=headers)
        if response.status_code == 200:
            response_body = response.json()  # JSON 형태의 응답 본문을 파싱합니다.
            print(response_body['message']['result']['translatedText'])
            return response_body['message']['result']['translatedText']
        else:
            print("Error Code:" + str(response.status_code))

# def main():
#   papago_translate("안녕하세요")

# if __name__ == "__main__":
#     main()

