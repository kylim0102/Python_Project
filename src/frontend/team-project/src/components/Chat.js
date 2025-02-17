import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import styles from '../css/chat.module.css';

const Chat = () => {
  const location = useLocation();
  const { personality, name: chatbotName = '챗봇' } = location.state || {};
  const [userInput, setUserInput] = useState('');
  const [currentDateTime, setCurrentDateTime] = useState('');
  const [error, setError] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingResponse, setIsProcessingResponse] = useState(false);
  const [audioHtml, setAudioHtml] = useState(null);
  const [messages, setMessages] = useState([]);
  const chatEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const inputRef = useRef(null); // 입력 필드 참조

  const searchTavily = async (query) => {
    try {
        const response = await fetch(`${process.env.REACT_APP_API_URL}/search-tavily`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });

        if (!response.ok) {
          throw new Error('서버 오류: ' + response.statusText);
        }

        const data = await response.json();

        // 데이터 확인 후 처리
        if (!data || !data.search_results) {
            console.error('검색 결과가 없습니다.');
            return []; // 검색 결과가 없으면 빈 배열 반환
        }

        console.log('검색 결과:', data.search_results);
        return data.search_results;  // 정상적으로 검색 결과 반환
    } catch (error) {
        console.error('검색 API 호출 중 오류 발생:', error);
        setError(error.message);
        return [];  // 오류 발생 시 빈 배열 반환
    }
};

  // 현재 날짜와 시간 가져오기
  const getCurrentDateTime = () => {
    const now = new Date();
    const date = now.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long',
    });
    const time = now.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
    return `${date} ${time}`;
  };

  // 시간만 가져오기
  const getTimeOnly = () => {
    const now = new Date();
    return now.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  };

  function askForCalendarHelp() {
    const userInput = "캘린더 사용법";  // 예시: 사용자가 '캘린더 사용법'이라고 입력했다고 가정

    fetch('/calendar-help', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ user_input: userInput })
    })
    .then(response => response.json())
    .then(data => {
        // 받은 캘린더 사용법을 사용자에게 출력
        console.log("캘린더 사용법:", data.response);
        //displayCalendarHelp(data.response);  // 사용자에게 결과 출력하는 함수
    })
    .catch(error => {
        console.error("오류 발생:", error);
    });
  }

  const addEventToGoogleCalendar = async (eventDetails) => {
    try {
      const eventWithReminder = {
        ...eventDetails,
        reminders: {
          useDefault: false,
          overrides: [
            {
              method: 'popup',
              minutes: 30,
            },
          ],
        },
      };
      const response = await fetch(`${process.env.REACT_APP_API_URL}/add-calendar-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventWithReminder),
      });
  
      if (!response.ok) {
        throw new Error('일정 추가 오류');
      }
  
      const data = await response.json();
      console.log('구글 캘린더에 일정이 추가되었습니다:', data);
      
    } catch (error) {
      console.error('구글 캘린더에 일정 추가 중 오류 발생:', error);
    }
  };

  const deleteEventToGoogleCalendar = async (eventDetails) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/delete-calendar-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventDetails),
      });

      if (!response.ok) {
        throw new Error('일정 삭제 오류');
      }

      const data = await response.json();
      console.log('구글 캘린더에 일정이 삭제되었습니다:', data);
    } catch (error) {
      console.error('구글 캘린더에 일정 삭제 중 오류 발생:', error);
    }
  };

  const deleteEventDateToGoogleCalendar = async (eventDetails) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/delete-calendar-date-event`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventDetails),
      });

      if (!response.ok) {
        throw new Error('일정 삭제 오류');
      }

      const data = await response.json();
      console.log('구글 캘린더에 일정이 삭제되었습니다:', data);
    } catch (error) {
      console.error('구글 캘린더에 일정 삭제 중 오류 발생:', error);
    }
  };

  const selectEventToGoogleCalendar = async (eventDetails) => {
    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/select-calendar-date-event`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventDetails),
      });

      if (!response.ok) {
        throw new Error('일정 불러오기 오류');
      }

      const data = await response.json();
      console.log('구글 캘린더에 있는 일정을 불러옵니다:', data);
    } catch (error) {
      console.error('구글 캘린더에 일정 불러오던 중 오류 발생:', error);
    }
  };

  // 메시지 추가 (중복 방지)
  const addMessage = (sender, message, time) => {
    setMessages((prevMessages) => {
      if (prevMessages.some((msg) => msg.sender === sender && msg.message === message && msg.time === time)) {
        return prevMessages; // 중복 메시지 방지
      }
      return [...prevMessages, { sender, message, time }];
    });
  };


  let isNotified = false; // 알림이 이미 설정되었는지 확인

  const handleScheduleNotification = (message) => {
    // 이미 알림이 설정되었으면 실행하지 않음
    if (isNotified) return;

    // "오늘" 뒤에 공백이 있을 수도 있고 없을 수도 있으므로 그에 맞는 정규식 적용
    const regex = /오늘\s*(.*?)(\d{1,2}시 \d{1,2}분)/;
    const match = message.match(regex);

    if (match) {
      const event = match[1].trim(); // "오늘"과 시간 사이의 텍스트 (예: 수업, 병원)
      const time = match[2];  // 시간 (예: 15시 39분)

      // 시간 추출
      const [hour, minute] = time.split('시').map(str => parseInt(str.replace('분', '').trim(), 10));
      
      const now = new Date();
      const scheduleTime = new Date(now);
      scheduleTime.setHours(hour, minute, 0, 0);

      const eventDetails = {
        summary: event,
        description: `오늘 ${event}`,
        start: {
          dateTime: scheduleTime.toISOString(),
          timeZone: 'Asia/Seoul',
        },
      };
  
      askForCalendarHelp();
      addEventToGoogleCalendar(eventDetails);  // 일정 추가 함수 호출
      deleteEventToGoogleCalendar(eventDetails);  //일정 삭제 함수 호출
      deleteEventDateToGoogleCalendar(eventDetails);
      selectEventToGoogleCalendar(eventDetails);
    }
  };

  // 음성 녹음 시작
  const startRecording = () => {
    if (isRecording || isProcessingResponse) return;

    audioChunksRef.current = [];

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ audio: true })
        .then((stream) => {
          mediaRecorderRef.current = new MediaRecorder(stream);

          mediaRecorderRef.current.ondataavailable = (event) => {
            audioChunksRef.current.push(event.data);
          };

          mediaRecorderRef.current.onstop = async () => {
            if (isProcessingResponse) return; // 중복 처리 방지
            setIsProcessingResponse(true);

            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/mp3' });
            const audioData = await audioBlob.arrayBuffer();
            const formData = new FormData();
            formData.set('chatbot_name', chatbotName);
            formData.set('personality', personality);
            formData.set('file', new Blob([audioData]), 'audio.mp3');

            try {
              const response = await fetch(`${process.env.REACT_APP_API_URL}/chat-audio`, {
                method: 'POST',
                body: formData,
              });

              if (!response.ok) {
                throw new Error('음성 파일 전송 오류');
              }

              const data = await response.json();
              const chatbotMessage = data.response;
              const newAudioHtml = data.audio_html;
              const recognizedText = data.transcribed_text;

              const sentTime = getTimeOnly();
              addMessage('사용자', recognizedText, sentTime);

              const receivedTime = getTimeOnly();
              addMessage(chatbotName, chatbotMessage, receivedTime);

              handleScheduleNotification(recognizedText);

              setAudioHtml(newAudioHtml);
              setUserInput('');
            } catch (error) {
              setError(error.message);
            } finally {
              setIsProcessingResponse(false);
            }
          };

          mediaRecorderRef.current.start();
          setIsRecording(true);
        })
        .catch((err) => {
          console.error('녹음 권한을 요청할 수 없습니다.', err);
        });
    }
  };

  // 음성 녹음 중지
  const stopRecording = () => {
    if (!isRecording) return;

    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    audioChunksRef.current = [];
  };

  // 텍스트 메시지 전송
  const handleSendMessage = async () => {
    if (isRecording || isProcessingResponse || userInput.trim() === '') return;
  
    const sentTime = getTimeOnly();
    const newMessage = { sender: '사용자', message: userInput, time: sentTime };
    setMessages((prevMessages) => [...prevMessages, newMessage]); // setChatHistory -> setMessages
    setUserInput('');  // 입력 필드 초기화
  
    try {
      setIsProcessingResponse(true);
      const response = await fetch(`${process.env.REACT_APP_API_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chatbotName: chatbotName,
          user_input: userInput,
          personality: personality,
        }),
      });
  
      // 응답 상태 확인
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || '서버 응답 오류');
      }
  
      // 서버 응답 처리
      const data = await response.json();
      console.log('챗봇 응답 데이터:', data);
      const chatbotMessage = data.response;
      const newAudioHtml = data.audio_html;
      
      if (!chatbotMessage) {
        const searchResults = await searchTavily(userInput);
        console.log('검색 결과:', searchResults);  // 검색 결과 확인
        if (response.results && response.results.length > 0) {
          // 검색 결과가 있는 경우
          const resultsMessage = response.results.map(result => `${result.title} - <a href="${result.url}">링크</a><br>내용: ${result.content}`).join("<br><br>");
          setMessages((prevMessages) => [
              ...prevMessages,
              { sender: chatbotName, message: `검색 결과:\n${resultsMessage}`, time: getTimeOnly() },
          ]);
      } else {
          setMessages((prevMessages) => [
            ...prevMessages,
            { sender: chatbotName, message: '검색 결과가 없습니다. 그러나, 관련된 웹사이트를 확인해 보세요!', time: getTimeOnly() },
          ]);
        }
      } else {
        const receivedTime = getTimeOnly();
        setMessages((prevMessages) => [
          ...prevMessages,
          { sender: chatbotName, message: chatbotMessage, time: receivedTime },
        ]);
      }
  
      // 메시지 전송 후에만 음성 HTML을 설정
      if (newAudioHtml) {
        setAudioHtml(newAudioHtml);
      } else {
        setAudioHtml(''); // 음성 HTML이 없으면 빈 값으로 설정
      }
  
    } catch (error) {
      console.error('Error fetching chatbot response:', error);
      if (error.message.includes('부적절한 내용')) {
        alert('부적절한 내용은 사용할 수 없습니다. 다시 입력해주세요.');
        setMessages((prevMessages) => prevMessages.slice(0, -1));  // 마지막 메시지 제거
      } else {
        setError(error.message);
      }
    } finally {
      setIsProcessingResponse(false);
    }
  };

  // Enter 키 눌렀을 때 메시지 전송
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && e.shiftKey) {
      // Shift + Enter일 때 줄 바꿈 처리
      setUserInput((prevInput) => prevInput + '\n');
    } else if (e.key === 'Enter' && !e.shiftKey) {
      // Enter만 누르면 메시지 전송
      handleSendMessage();
    }
  };

  // 에러 메시지 표시
  const displayErrorMessage = useCallback(() => {
    return error ? <div className={styles.errorMessage}>{error}</div> : null;
  }, [error]);

  // 채팅 기록 가져오기
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentDateTime(getCurrentDateTime());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // 채팅 기록에 변화가 있을 때 자동으로 스크롤
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <div className={styles.chatContainer}>
      <div className={styles.chatDataTime}>
        <strong>{currentDateTime}</strong>
      </div>
      <div className={styles.chatHistory}>
        {messages.map((msg, index) => (
          <div
            key={index}
            className={msg.sender === '사용자' ? styles.chatMessageUser : styles.chatMessageChatbot}
          >
            <strong>{msg.sender === '사용자' ? '사용자' : chatbotName}:</strong>
            <div dangerouslySetInnerHTML={{__html:msg.message}}></div>
            <div className={msg.sender === '사용자' ? styles.chatTimeUser : styles.chatTimeChatbot}>
              <em>{msg.time}</em>
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>
      <div className={styles.chatInputArea}>
        <input
          ref={inputRef}
          type="text"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          className={styles.chatSendButton}
          onClick={handleSendMessage}
          disabled={isRecording || isProcessingResponse}
        >
          전송
        </button>
        <button
          className={styles.voiceButton}
          onClick={isRecording ? stopRecording : startRecording}
        >
          {isRecording ? '녹음 중지' : '음성 인식 시작'}
        </button>
      </div>
      {displayErrorMessage()}
      {!isRecording && !isProcessingResponse && audioHtml && userInput.trim() === '' && (
        <div dangerouslySetInnerHTML={{ __html: audioHtml }} />
      )}
    </div>
  );
};

export default Chat;
