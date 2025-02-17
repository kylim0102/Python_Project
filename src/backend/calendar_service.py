import os
import re
from datetime import datetime, timedelta
import pickle
from pymongo import MongoClient
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI
import pytz

from dotenv import load_dotenv
load_dotenv()

# MongoDB 설정
mongo_client = MongoClient('localhost', 27017)
db = mongo_client.project
collection = db.chat_history

today = datetime.today().strftime('%Y년 %m월 %d일')
client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))

def explain_calendar_usage():
    # 캘린더 사용에 대한 설명
    text = """캘린더 사용법에 대해 알려드리겠습니다. \n\n

    1. **일정 추가**: 일정을 추가하려면 다음과 같이 입력해주세요. \n
    예: 일정 추가: 회의 2025-02-03 10:00 ~ 12:00 \n
    또는 일정 추가: 휴가 2025-02-03 종일 \n
    - 일정 제목, 날짜, 시간 정보를 포함해야 합니다. \n\n

    2. **일정 삭제**: 특정 일정을 삭제하려면 날짜와 시간을 포함하여 삭제 요청을 하세요. \n
    예: 일정 삭제: 회의 2025-02-03 10:00 \n\n

    3. **일정 조회**: 특정 날짜에 일정을 조회하려면 날짜를 입력하세요. \n
    예: 일정 조회: 2025-02-03 \n\n

    캘린더 기능을 통해 더 효율적으로 일정을 관리할 수 있습니다. 추가적인 질문이 있으면 언제든지 물어보세요!"""
        
    return text

def explain_user_input(user_input: str):
    # 사용자가 "캘린더" 또는 "일정" 관련 키워드를 포함할 경우 캘린더 사용법 안내
    if "캘린더" in user_input or "일정" in user_input:
        return explain_calendar_usage()
    return None

def extract_event_info(user_input: str):
    insert_event_prompt = ChatPromptTemplate.from_template(
        f"User: {user_input}\n"
        f"오늘 날짜는 {today}야.\n"
        f"다음은 일정을 추가하기 위한 명령어 형식이야:\n"
        f"일정 추가: <일정 제목> <YYYY-MM-DD> <HH:MM> ~ <YYYY-MM-DD><HH:MM>\n"
        f"시간이 없을때는 \n"
        f"일정 추가: <일정 제목> <YYYY-MM-DD>\n"
        f"너는 사용자의 요청을 이 형식으로 변환해야 해."
    )

    formatted_prompt = insert_event_prompt.format_prompt(user_input=user_input).to_string()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                 {"role": "user", "content": formatted_prompt}],
        temperature=0.3
    )

    result = response.choices[0].message.content.strip()
    print("응답 결과:", result)  # 디버깅을 위한 로그 추가

    # 시간 있는 일정 추출
    match = re.search(r"일정 추가: (.+?) (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) ~ (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", result)

    if match:
        summary = match.group(1)
        start_date = match.group(2)
        start_time = match.group(3)
        end_date = match.group(4)
        end_time = match.group(5)
        start_datetime = f"{start_date}T{start_time}:00"
        end_datetime = f"{end_date}T{end_time}:00"
        return {"summary": summary, "start_datetime": start_datetime, "end_datetime": end_datetime}

    # 종일 일정 추출 (시간 없는 일정)
    match_all_day = re.search(r"일정 추가: (.+?) (\d{4}-\d{2}-\d{2})", result)

    if match_all_day:
        summary = match_all_day.group(1)
        start_date = match_all_day.group(2)
        print("추출된 start_date:", start_date)  # 디버깅을 위한 로그 추가
        return {"summary": summary, "start_date": start_date, "end_date": start_date}
    
    return None

def extract_event_delete(user_input: str):
    delete_event_prompt = ChatPromptTemplate.from_template(
        f"User: {user_input}\n"
        f"오늘 날짜는 {today}야."
        f"다음은 일정을 삭제하기 위한 명령어 형식이야:\n"
        f"일정 삭제: <일정 제목> <YYYY-MM-DD> <HH:MM>\n"
        f"너는 사용자의 요청을 이 형식으로 변환해야 해."
    )
    formatted_prompt = delete_event_prompt.format_prompt(user_input=user_input).to_string()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                 {"role": "user", "content": formatted_prompt}],
        temperature=0.3
    )

    result = response.choices[0].message.content.strip()

    match = re.search(r"일정 삭제: (.+?) (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", result)
    if match:
        summary = match.group(1)
        start_date = match.group(2)
        start_time = match.group(3)
        
        # start_date와 start_time을 datetime으로 결합하여 변환
        start_datetime = datetime.strptime(f"{start_date}T{start_time}", "%Y-%m-%dT%H:%M")
        
        return {"summary": summary, "start_datetime": start_datetime}
    else:
        return None, None
    
def extract_event_delete_date(user_input: str):
    today = datetime.today().strftime('%Y-%m-%d')  # 오늘 날짜 가져오기
    
    # 날짜를 추출하기 위한 프롬프트 템플릿
    delete_event_date_prompt = ChatPromptTemplate.from_template(
        f"User: {user_input}\n"
        f"오늘 날짜는 {today}야.\n"
        f"다음은 일정을 삭제하기 위한 명령어 형식이야:\n"
        f"일정 삭제: <YYYY-MM-DD>\n"
        f"너는 사용자의 요청을 이 형식으로 변환해야 해."
    )
    
    # 포맷된 프롬프트 만들기
    formatted_prompt = delete_event_date_prompt.format_prompt(user_input=user_input).to_string()
    
    try:
        # GPT 응답 얻기
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": formatted_prompt}],
            temperature=0.3
        )

        result = response.choices[0].message.content.strip()

        # 날짜 패턴 추출
        match = re.search(r"일정 삭제: (\d{4}-\d{2}-\d{2})", result)
        
        if match:
            start_date = match.group(1)  # 날짜 (YYYY-MM-DD)
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")  # datetime 객체로 변환
            return {"start_datetime": start_datetime}
        else:
            return None
    except Exception as e:
        return None
    
def extract_find_event_info(user_input: str):
    select_event_prompt = ChatPromptTemplate.from_template(
        f"User: {user_input}\n"
        f"오늘 날짜는 {today}야.\n"
        f"다음은 일정을 가져오기 위한 명령어 형식이야:\n"
        f"일정 가져오기: <YYYY-MM-DD>\n"
        f"너는 사용자의 요청을 이 형식으로 변환해야 해."
    )

    formatted_prompt = select_event_prompt.format_prompt(user_input=user_input).to_string()
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": formatted_prompt}],
            temperature=0.3
        )

        result = response.choices[0].message.content.strip()

        match = re.search(r"일정 가져오기: (\d{4}-\d{2}-\d{2})", result)

        if match:
            start_date = match.group(1)  # 날짜 (YYYY-MM-DD)
            start_datetime = datetime.strptime(start_date, "%Y-%m-%d")  # datetime 객체로 변환
            return {"start_datetime": start_datetime}
            
        else:
            return None
    except Exception as e:
        return None

# Google Calendar API 인증 및 서비스 생성
def authenticate_google_account():
    creds = None
    # 토큰이 이미 저장되어 있으면 가져옵니다.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # 유효하지 않으면 새로운 인증을 진행합니다.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', ['https://www.googleapis.com/auth/calendar']
            )
            creds = flow.run_local_server(port=0)

        # 인증 정보를 저장합니다.
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    # 구글 캘린더 API 서비스 객체 반환
    service = build('calendar', 'v3', credentials=creds)
    return service

# 일정 추가
def add_event_to_calendar(summary, start_datetime=None, end_datetime=None, start_date=None, end_date=None):
    try:
        service = authenticate_google_account()
        
        # 종일 일정인 경우
        if start_date and end_date:
            event = {
                'summary': summary,
                'start': {
                    'date': start_date,
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'date': end_date,
                    'timeZone': 'Asia/Seoul',
                },
            }
        # 시간 있는 일정인 경우
        elif start_datetime and end_datetime:
            event = {
                'summary': summary,
                'start': {
                    'dateTime': start_datetime,
                    'timeZone': 'Asia/Seoul',
                },
                'end': {
                    'dateTime': end_datetime,
                    'timeZone': 'Asia/Seoul',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {
                            'method': 'popup',  # 팝업 알림
                            'minutes': 30,      # 10분 전에 알림
                        },
                    ],
                },
            }
        else:
            return "필요한 날짜 정보가 없습니다."
        
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return "일정 추가했어."
    
    except HttpError as error:
        return f"일정을 추가하는 데 오류가 발생했습니다: {error}"

# 일정 삭제 (이름과 시간으로)
def delete_event_from_calendar(summary, start_datetime):
    try:
        service = authenticate_google_account()

        timezone = pytz.timezone('Asia/Seoul')
        start_datetime = timezone.localize(start_datetime)  # start_datetime에 시간대 추가
        end_datetime = start_datetime + timedelta(days=1)
        
        start_time_str = start_datetime.isoformat()
        end_time_str = end_datetime.isoformat()

        # Google Calendar에서 일정을 검색
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=start_time_str, 
            timeMax=end_time_str,
            singleEvents=True, 
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        if not events:
            return f"{start_datetime.strftime('%Y-%m-%d %H:%M')}에 해당하는 일정이 없어."

        event_found = False
        
        for event in events:
            if summary.lower() in event['summary'].lower():  # 일정 이름으로 검색
                event_id = event['id']
                # 일정 삭제
                service.events().delete(calendarId='primary', eventId=event_id).execute()
                event_found = True
                break  # 일정을 찾으면 루프 종료

        if event_found:
            return f"일정 '{summary}'가 삭제됬어."
        else:
            return f"일정 이름 '{summary}'이(가) {start_datetime.strftime('%Y-%m-%d %H:%M')}에 존재하지 않아."
    except HttpError as error:
        return f"Google Calendar API에서 오류가 발생했습니다: {error}"
    
    except Exception as e:
        return f"일정을 삭제하는데 오류가 발생했습니다: {e}"

# 날짜별 일정 삭제
def delete_event_from_date(start_datetime):
    try:
        service = authenticate_google_account()

        timezone = pytz.timezone('Asia/Seoul')
        
        start_datetime = timezone.localize(start_datetime)  # start_datetime에 시간대 추가

        start_time_str = start_datetime.isoformat()  # 정확한 시작 시간

        # 다음 날로 end_time 설정
        end_datetime = start_datetime + timedelta(days=1)
        end_time_str = end_datetime.isoformat()  # 정확한 종료 시간

        events_result = service.events().list(
            calendarId='primary', 
            timeMin=start_time_str, 
            timeMax=end_time_str,  # end_time을 이용하여 하루를 처리
            singleEvents=True, 
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        if not events:
            return f"{start_datetime.strftime('%Y-%m-%d')}에 해당하는 일정이 없어."

        event_found = False
        
        for event in events:
            # 이름에 상관없이 모든 일정을 삭제
            event_id = event['id']
            # 일정 삭제
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            event_found = True

        if event_found:
            return f"{start_datetime.strftime('%Y-%m-%d')}의 모든 일정이 삭제됐어."
        else:
            return f"{start_datetime.strftime('%Y-%m-%d')}에 삭제할 일정이 없어."

    except Exception as e:
        return f"일정을 삭제하는데 오류가 발생했습니다: {e}"

# 날짜 포맷 함수 추가
def format_datetime(iso_datetime):
    try:
        # ISO 형식의 문자열을 datetime 객체로 변환
        dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
        # 원하는 형식으로 변환
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_datetime  # date 형식으로 들어온 경우 그대로 반환

# 날짜로 일정 찾기
def find_event_by_date(start_datetime):
    try:
        service = authenticate_google_account()

        timezone = pytz.timezone('Asia/Seoul')
        start_datetime = timezone.localize(start_datetime)  # 시간대 추가

        start_time_str = start_datetime.isoformat()  # 날짜 시작 시간 (00:00)
        end_datetime = start_datetime + timedelta(days=1)
        end_time_str = end_datetime.isoformat()  # 날짜 종료 시간 (23:59)

        # Google Calendar에서 일정을 검색
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_time_str,
            timeMax=end_time_str,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        
        if not events:
            return f"{start_datetime.strftime('%Y-%m-%d')}에 해당하는 일정이 없어."

        event_list = []
        for idx, event in enumerate(events, start=1):
            event_summary = event['summary']
            event_start = event['start'].get('dateTime', event['start'].get('date'))
            event_end = event['end'].get('dateTime', event['end'].get('date'))
            
            # 날짜 포맷 적용
            formatted_start = format_datetime(event_start)
            formatted_end = format_datetime(event_end)
            
            event_list.append(f"{idx}.일정: {event_summary}\n 시작: {formatted_start}\n 종료: {formatted_end} \n\n")
        
        return "\n".join(event_list)

    except HttpError as error:
        return f"일정을 찾는 데 오류가 발생했습니다: {error}"

    except Exception as e:
        return f"일정을 찾는 중 오류가 발생했습니다: {e}"
                