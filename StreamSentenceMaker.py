class StreamSentenceProcessor:
    def __init__(self):
        self.current_sentence = ""
        
    def process_word(self, json_data):
        word = json_data.get("transcription", {}).get("text", "")
        
        # 단어 추가 전 후행 공백 제거 및 연속 공백 처리를 위해 한 칸 공백 추가
        if word.strip() != "":
            self.current_sentence += " " + word
        else:
            # 입력된 단어가 공백일 경우, 현재 문장에 공백 추가
            self.current_sentence += " "
        
        # 연속된 공백이 2번 이상 들어오는 경우를 체크하기 위한 조건 추가
        consecutive_spaces = self.current_sentence.count("   ")  # 두 개 이상의 공백을 카운트
        
        # 문장의 완성 여부 확인
        if (self.current_sentence.strip() == "" or 
            '.' in self.current_sentence or 
            consecutive_spaces > 0):  # 연속된 공백이 2번 이상인 경우도 포함
            # 문장이 마침표로 끝나면 해당 위치까지, 아니면 현재까지의 전체 문장을 완성 문장으로 처리
            end_index = self.current_sentence.find('.') + 1 if '.' in self.current_sentence else len(self.current_sentence)
            completed_sentence = self.current_sentence[:end_index].strip()
            self.current_sentence = self.current_sentence[end_index:].strip()  # 다음 문장을 위해 나머지 부분 저장
            return completed_sentence
        else:
            return None
