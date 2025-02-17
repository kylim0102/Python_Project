from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from chatbot_setting import app as chatbot_setting_app
from chatbot_response import app as chatbot_response_app

app = FastAPI()

# CORS 설정 (React 앱이 사용하는 도메인 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 앱의 URL
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메소드 허용
    allow_headers=["*"],  # 모든 HTTP 헤더 허용
)

@app.options("/chat")
async def options_chat():
    return {}

# 챗봇 관련 라우트 포함
app.include_router(chatbot_setting_app)
app.include_router(chatbot_response_app)