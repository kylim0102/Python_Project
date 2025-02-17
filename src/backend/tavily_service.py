import os
import requests
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv
from rich import print as rprint

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def search_with_tavily(query):
    url = "https://api.tavily.com/search"
    headers = {"Authorization": f"Bearer {TAVILY_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "query": query,
        "search_depth": "full",
        "max_results": 1,
        "include_images": False
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 처리
        data = response.json()

        # 응답 데이터 확인 후 반환
        if 'results' in data:
            return data['results']  # 결과 반환
        else:
            return None  # 결과 없음 처리

    except requests.exceptions.RequestException as e:
        return None  # 요청 실패 처리

def generate_response_with_langchain(query):
    llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7, openai_api_key=OPENAI_API_KEY)
    tools = [TavilySearchResults(max_results=1)]
    memory = ConversationBufferMemory(memory_key="chat-history")
    
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        memory=memory
    )
    
    # Tavily 결과 가져오기
    try:
        tavily_results = search_with_tavily(query)
        
        if not tavily_results or 'results' not in tavily_results or not tavily_results['results']:
            return "검색 결과가 없습니다. 다른 질문을 시도해보세요."
        
        # Tavily 결과에서 필요한 데이터 추출
        results_text = "\n".join([f"제목: {result['title']}\n URL: {result['url']}\n 내용: {result.get('content', '내용 없음')[:100000]}\n"
                                 for result in tavily_results['results']])
        
        # Langchain 에이전트를 통해 응답 생성
        query_with_results = f"검색된 결과: {results_text}. 이에 대한 설명을 제공해 주세요."
        
        response = agent.run(query_with_results)
        if not response:
            raise ValueError("응답이 비어 있습니다.")
        return response
    
    except Exception as e:
        return "챗봇에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."