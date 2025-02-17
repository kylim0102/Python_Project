import os
import re
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from openai import OpenAI
from datetime import datetime
from pymongo import MongoClient
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate
from korean_bad_words import filter_profanity
from calendar_service import add_event_to_calendar, delete_event_from_calendar, delete_event_from_date, find_event_by_date, extract_event_info, extract_event_delete, extract_event_delete_date, extract_find_event_info, explain_user_input, explain_calendar_usage
from weather import get_weather, extract_city
from weather import get_weather, extract_city
from chat_audio import TTS, STT
import json
from tavily_service import generate_response_with_langchain, search_with_tavily

load_dotenv()

# 환경 변수 설정
client = OpenAI(api_key=os.getenv("OPEN_API_KEY"))

# MongoDB 설정
mongo_client = MongoClient('localhost', 27017)
db = mongo_client.project
collection = db.chat_history

# ConversationBufferMemory 설정
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

today = datetime.today().strftime('%Y년 %m월 %d일')

tools = {
    "일정 추가 대화": {"tool": add_event_to_calendar, "extractor": extract_event_info, "args": ["summary", "start_datetime", "end_datetime", "start_date", "end_date"]},
    "일정 삭제 대화": {"tool": delete_event_from_calendar, "extractor": extract_event_delete, "args": ["summary", "start_datetime"]},
    "일정 전체 삭제 대화": {"tool": delete_event_from_date, "extractor": extract_event_delete_date, "args": ["start_datetime"]},
    "일정 요청": {"tool": find_event_by_date, "extractor": extract_find_event_info, "args": ["start_datetime"]},
    "날씨 요청": {"tool": get_weather, "extractor": extract_city, "args": ["city"]},
    "캘린더 사용법": {"tool": explain_user_input, "extractor":explain_calendar_usage, "args": ["user_input"]},
    "지식 없음": {"tool": generate_response_with_langchain, "extractor": None, "args": ["query"]}
}

# 사용자 의도를 분석하는 함수
def analyze_intent(user_input: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages = [
                {
                    "role": "system",
                    "content": f"오늘은 {today}야. "
                        "You are an assistant specialized in identifying user intents. "
                        "Your task is to classify the user's input into one of the following categories: "
                        "'날씨 요청', '일정 추가 대화', '일정 삭제 대화', '일정 전체 삭제 대화', '일정 요청', '캘린더 사용법', '일반 대화', or '지식 없음'. "
                        "**You must always classify the user's input into exactly one of these categories.** "
                        "There are no exceptions. Do not create new categories or return an empty classification. "

                        "If the user's input is a simple greeting, casual conversation, or a non-specific question that does not require factual or external data, classify it as '일반 대화'. "
                        "If the user's input asks, 'What did I say?' or something similar, classify it as '일반 대화' since it is a request for past conversation context."
                        "If the user's input asks for real-time external data (e.g., news, stock prices, events), classify it as '지식 없음'. "
                        "For calendar-related interactions, classify accordingly (e.g., '일정 추가 대화', '일정 요청'). "

                        "**Tool Usage Rules:** "
                        "- If category is '날씨 요청', call the 'get_weather' tool."
                        "- If category is '일정 추가 대화', call the 'add_event_to_calendar' tool."
                        "- If category is '일정 삭제 대화', call the 'delete_event_from_calendar' tool."
                        "- If category is '일정 전체 삭제 대화', call the 'delete_event_from_date' tool."
                        "- If category is '일정 요청', call the 'find_event_by_date' tool."
                        "- If category is '캘린더 사용법', call the 'explain_user_input' tool."
                        "- If category is '지식 없음', call the 'generate_response_with_langchain' tool."

                        "Ensure the response follows this structured JSON format:"
                        "{"
                        "  'intent': '<classified_intent>',"
                        "  'category': '<category>',"
                        "  'description': '<brief_explanation>'"
                        "}"
                },
                {
                    "role": "user", 
                    "content": f"'{user_input}'가 말한 의도를 무조건 파악해서 말해. "
                            "답변은 의도(intent), 카테고리(category), 설명(description)을 포함한 구조화된 JSON 형식으로만 출력해."
                }
            ],
            temperature=0.3
        )

        # 응답에서 의도 추출
        content = response.choices[0].message.content.strip()
        if content:
            response_json = json.loads(content.strip('json\n').strip(''))
            print(response_json)
            return response_json.get("category", "일반 대화")
        else:
            raise ValueError("응답 내용이 비어 있습니다.")

    except json.JSONDecodeError:
        return "응답을 JSON 형식으로 파싱할 수 없습니다."
    except Exception as e:
        return f"서버 오류: {str(e)}"

# ConversationBufferMemory 설정
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# 챗봇 응답 함수
def chatbot_response(user_input, personality, chatbotName):
    category = analyze_intent(user_input)

    if category != "일반 대화":
        return handle_intent(category, user_input)
    
    # 채팅 기록을 MongoDB에 저장
    chat_data = {
        "user_input": user_input,
        "personality": personality,
        "chatbot_name": chatbotName,
        "category": category,
        "timestamp": datetime.now()
    }
    collection.insert_one(chat_data)  # MongoDB에 기록 저장

    # 대화 내용 메모리에 저장
    memory.buffer.append({"role": "user", "content": user_input})  # 사용자 메시지 추가

    if "이름" in user_input or "너 이름" in user_input:
        return f"내 이름은 {chatbotName}(이)야."

    if personality == 'T':
        prompt_template = ChatPromptTemplate.from_template(
            f"User: {user_input}\n"
            f"오늘 날짜는 {today}야. 오래된 친구랑 대화하듯이 답장해줘. "
            f"상대방의 감정에 크게 휘둘리지 않고, 상황을 빠르게 파악해서 문제 해결 중심으로 실용적인 답변을 해줘. "
            f"꼭 필요한 정보만 골라서 핵심만 간단명료하게 전달해줘. "
            f"어려운 상황이라도 감정적인 접근보다는 현실적으로 해결책을 제안하고, 도움이 될 만한 구체적인 방법을 말해줘. "
            f"일상적인 주제는 복잡하게 고민하지 말고, 최대한 간결하고 실용적으로 접근해. "
            f"전문적인 주제라면, 핵심 개념을 쉽게 정리해서 전달하고, 필요한 경우 간단한 예시를 들어 설명해. "
            f"답변은 길게 쓰지 말고, 직설적이고 간결하게 1-2 문장으로 끝내줘. "
            f"단, 존댓말을 사용하지 말고 친근하게 대화해."
        )
        prompt = prompt_template.format(user_input=user_input)
        temperature = 0.3
    else:
        prompt_template = ChatPromptTemplate.from_template(
            f"User: {user_input}\n"
            f"오늘 날짜는 {today}야. 진심으로 따뜻하고 다정하게 오래된 친구랑 대화하듯이 답장해줘. "
            f"상대방의 감정에 공감하면서 대화를 시작해줘. "
            f"상대방이 힘들거나 고민이 있는 것 같다면 먼저 공감의 말을 건네줘. 예를 들어, '그럴 땐 정말 속상했겠다' "
            f"혹은 '괜찮아, 네 마음 이해해'처럼 말하며 상대방이 편하게 느낄 수 있도록 배려해줘. "
            f"상대방이 무슨 일을 겪었는지 자연스럽게 물어봐서 대화를 이어갈 수 있게 도와줘. "
            f"만약 상대방이 감정 상태를 명확히 드러내지 않았다면, 긍정적이고 따뜻한 분위기를 만들어 주고 "
            f"상대방이 자신감을 느낄 수 있도록 응원과 격려의 말을 건네줘. "
            f"일상적인 주제에서는 상대방이 더 얘기하고 싶게 만드는 질문을 던지고, 가볍게 웃을 수 있는 분위기를 만들어줘. "
            f"전문적인 주제라면 상대방이 이해하기 쉬운 말로 설명해주고, 필요할 경우 구체적인 사례나 경험을 공유해줘. "
            f"답변은 길지 않게 1-2 문장 내로, 상대방을 진심으로 배려하는 마음을 담아 대화해줘. "
            f"단, 존댓말을 사용하지 말고, 친근하게 친구처럼 얘기해."
        )
        prompt = prompt_template.format(user_input=user_input)
        temperature = 1.0

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=memory.buffer + [{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}],
            temperature=temperature
        )

        # 응답 후에도 MongoDB에 저장할 수 있음
        chat_history = {
            "user_input": user_input,
            "response": response.choices[0].message.content.strip(),
            "timestamp": datetime.now()
        }
        collection.insert_one(chat_history)

        # 대화 내용 메모리에 저장
        memory.buffer.append({"role": "assistant", "content": response.choices[0].message.content.strip()})  # 챗봇 응답 메시지 추가
        if not response.choices or not response.choices[0].message.content:
            return "응답을 생성할 수 없습니다."
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error: {str(e)}"

def handle_intent(category, user_input):
    if category == "캘린더 사용법":
        return explain_user_input(user_input)
    
    if category == "지식 없음":  # Tavily를 사용하여 외부 데이터를 가져오도록 설정
        tavily_results = search_with_tavily(user_input)  # Tavily로 검색

        if tavily_results:
            response_message = "검색 결과\n"
            for result in tavily_results:
                content = result.get('content', '내용 없음')[:100000]
                # URL을 감지하고 <a> 태그로 변환
                content = re.sub(r'(https?://[^\s]+)', r'<a href="\1" target="_blank">\1</a>', content)
                response_message += f"제목: {result['title']}\nURL: <a href='{result['url']}' target='_blank'>{result['url']}</a>\n내용: {content}\n\n"
            return response_message.strip()
        else:
            return "검색 결과가 없습니다.\n"
    
    elif category in tools:
        tool_info = tools[category]
        extractor = tool_info["extractor"]
        tool = tool_info["tool"]
        args = tool_info["args"]
        if tool is None:
            return "적절한 도구가 없습니다."

        # 추출기 함수를 사용하여 필요한 데이터 추출
        extracted_data = extractor(user_input)

        # 추출된 데이터가 유효하면 tool을 호출
        if extracted_data:
            print(f"Calling {tool.__name__} with extracted_data={extracted_data}...")

            kwargs = {}
            for arg in args:
                if arg in extracted_data:
                    kwargs[arg] = extracted_data[arg]
                else:
                    if arg == "start_datetime" or arg == "end_datetime":
                        # 만약 datetime 값이 없으면 date 값으로 처리
                        date_key = arg.replace("datetime", "date")
                        if date_key in extracted_data:
                            kwargs[arg] = f"{extracted_data[date_key]}T00:00:00"
                    else:
                        if arg in ["start_date", "end_date"] and "start_datetime" in extracted_data:
                            continue
                        return f"필요한 인자 '{arg}'가 추출되지 않았습니다."

            # tool 호출 시 kwargs로 인자 전달
            return tool(**kwargs)
        else:
            return "입력된 정보가 유효하지 않습니다."

    return "알 수 없는 의도입니다."

# FastAPI 설정
app = APIRouter()

class ChatRequest(BaseModel):
    user_input: str
    personality: str
    chatbotName: str

@app.post("/chat")
async def get_chatbot_response(chat_request: ChatRequest):
    try:
        if filter_profanity(chat_request.user_input):
            raise HTTPException(
                status_code=400,
                detail="부적절한 내용이 포함되어 있습니다. 다시 작성해주세요."
            )

        response = chatbot_response(chat_request.user_input, chat_request.personality, chat_request.chatbotName)
        return {"response": response}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(e)}")

@app.post("/chat-audio")
async def process_audio(
    file: UploadFile = File(...),
    chatbot_name: str = Form(...),
    personality: str = Form(...),
):
    audio_data = await file.read()

    # STT를 사용하여 음성 인식 결과 텍스트로 변환
    question = STT(audio_data)

    # chatbot_response를 사용하여 응답 생성
    gpt_response = chatbot_response(user_input=question, personality=personality, chatbotName=chatbot_name)

    # TTS로 GPT 응답을 음성화
    audio_html = TTS(gpt_response)

    return {"transcribed_text": question, "response": gpt_response, "audio_html": audio_html}

# TTSRequest 모델 정의
class TTSRequest(BaseModel):
    text: str  # 텍스트 필드를 정의

@app.post("/whisper-tts")
async def whisper_tts(tts_request: TTSRequest):
    try:
        # 텍스트를 음성으로 변환
        audio_html = TTS(tts_request.text)
        return {"audio_html": audio_html}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"음성 알림 처리 오류: {str(e)}")
    
@app.post("/calendar-help")
async def calendar_help(user_input: str):
    try:
        # 사용자가 요청한 입력에 대해 캘린더 사용법을 설명하는 함수 호출
        response = explain_user_input(user_input)
        return {"response": response}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(e)}")

class CalendarEventRequest(BaseModel):
    action: str  # 'add' 또는 'delete'
    summary: str
    description: str = ""
    start_time: str  # 예: '2025-01-23T14:00:00'
    end_time: str  # 예: '2025-01-23T15:00:00'
    event_id: str = None  # 삭제할 때 사용

@app.post("/calendar")
async def manage_calendar_event(calendar_request: CalendarEventRequest):
    try:
        # description이 없으면 빈 문자열로 처리
        description = calendar_request.description or ""

        if calendar_request.action == 'add':
            response = add_event_to_calendar(
                summary=calendar_request.summary,
                start_time=calendar_request.start_time,
                end_time=calendar_request.end_time
            )
            return {"response": response}
        
        elif calendar_request.action == 'delete':
            response = delete_event_from_calendar(
                summary=calendar_request.summary,
                start_date=calendar_request.start_time
            )
            return {"response": response}
        
        elif calendar_request.action == 'delete_date':
            response = delete_event_from_date(
                start_datetime=calendar_request.start_time
            )
            return {"response": response}
        
        elif calendar_request.action == 'select':
            response = find_event_by_date(
                start_datetime=calendar_request.start_time
            )
            return {"response": response}
        else:
            raise HTTPException(status_code=400, detail="잘못된 요청입니다.")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(e)}")
    
@app.post("/search-tavily")
async def search_tavily(query: str):
    try:
        # Tavily API를 이용하여 쿼리 검색
        search_results = search_with_tavily(query)

        # search_results가 비어 있지 않으면 반환
        if search_results:
            return {"results": search_results}
        else:
            # 검색 결과가 없을 경우의 처리
            return {"message": "검색 결과를 찾을 수 없습니다."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 오류가 발생했습니다: {str(e)}")