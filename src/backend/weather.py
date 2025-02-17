import os
import re
from dotenv import load_dotenv
from openai import OpenAI
import requests
from datetime import datetime
from pymongo import MongoClient
from langchain.memory import ConversationBufferMemory

load_dotenv()

# MongoDB 설정
mongo_client = MongoClient('localhost', 27017)
db = mongo_client.project
collection = db.chat_history

# 환경 변수 설정
API_KEY = os.getenv("API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))

today = datetime.today().strftime('%Y년 %m월 %d일')

# 도시명을 영어로 번역하는 함수
def translate_to_english(city: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[ 
                {"role": "system", "content": f"오늘 날짜는 {today}야. 너는 사용자의 입력을 영어로 번역하는 역할을 해. 도시 이름만 번역하고 다른 단어는 포함하지 마."},
                {"role": "user", "content": f"한국의 도시 '{city}'를 정확히 영어로 번역해줘. 번역된 도시명만 출력해."}
            ],
            temperature=1.0
        )
        translated_city = response.choices[0].message.content.strip()
        return translated_city
    except Exception as e:
        return None

# 날씨 정보를 가져오는 함수
def get_weather(city: str):
    city_in_english = translate_to_english(city)  # 도시명을 영어로 변환
    if not city_in_english:
        return "도시명 번역에 실패했습니다."
    if not API_KEY:
        return "API_KEY가 설정되지 않았습니다. 환경 변수를 확인해주세요."

    params = {
        'q': city_in_english,
        'appid': API_KEY,
        'units': 'metric',
        'lang': 'kr'
    }

    try:
        response = requests.get(BASE_URL, params=params)

        if response.status_code == 200:
            data = response.json()
            weather = data['weather'][0]['description']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            weather_info = f"{city}의 날씨는 {weather}이며, 기온은 {temp:.0f}°C, 체감온도는 {feels_like:.0f}°C야."
            
            # MongoDB에 날씨 정보 저장
            weather_data = {
                'city': city,
                'weather_info': weather_info,
                'date': today  # 저장된 날짜
            }
            collection.insert_one(weather_data)  # 데이터 삽입
            
            return weather_info
        else:
            return f"날씨 정보를 가져오는 데 실패했습니다. 오류 코드: {response.status_code} 메시지: {response.text}"
    except requests.exceptions.RequestException as e:
        return f"API 요청 중 오류가 발생했습니다: {str(e)}"
    
# ConversationBufferMemory 설정
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 사용자 입력에서 지역명을 추출하는 함수
def extract_city(user_input: str):
    match = re.search(r"(?:오늘\s*)?(\S+)\s*(?:날씨)", user_input)  # '오늘'이나 '날씨'를 정확히 처리
    if match:
        return {"city": match.group(1).strip()}  # 도시명만 딕셔너리 형태로 반환
    return None