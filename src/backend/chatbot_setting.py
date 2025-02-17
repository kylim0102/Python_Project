from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

app = APIRouter()

# 설정 값을 저장할 변수
user_settings = {}

# 요청 데이터를 받을 Pydantic 모델 정의
class SettingsRequest(BaseModel):
    personality: str
    name: str

@app.post("/settings")
async def update_settings(settings: SettingsRequest):
    if settings.personality not in ["T", "F"]:
        raise HTTPException(status_code=422, detail="Invalid settings")

    # 사용자 설정 저장
    user_settings['personality'] = settings.personality
    user_settings['name'] = settings.name

    return {"message": "Settings updated successfully"}
