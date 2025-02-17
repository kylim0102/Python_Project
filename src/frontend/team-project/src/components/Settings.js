import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from '../css/Settings.module.css'

function Settings() {
  const [personality, setPersonality] = useState('');
  const [chatbotName, setChatbotName] = useState('');  // 챗봇 이름을 저장할 상태
  const [currentDateTime, setCurrentDateTime] = useState('');
  const navigate = useNavigate();

  // 현재 날짜와 시간을 반환하는 함수 (24시간 기준, 분까지만 표시)
  const getCurrentDateTime = () => {
    const now = new Date();
    const date = now.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'long',  // 요일을 포함하도록 설정
    }); // 예: "2025년 1월 11일 금요일"
    const time = now.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false, // 24시간 형식
    }); // 예: "15:05"

    return `${date} ${time}`; // 예: "2025년 1월 11일 금요일 15:05"
  };

  // 컴포넌트가 마운트될 때마다 시간을 갱신하도록 설정
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentDateTime(getCurrentDateTime());
    }, 1000); // 1초마다 시간을 갱신

    // 처음에 한 번 바로 시간을 갱신
    setCurrentDateTime(getCurrentDateTime());

    // 컴포넌트가 언마운트될 때 interval을 클리어
    return () => clearInterval(interval);
  }, []);

  const handleSave = async () => {
    if (personality && chatbotName) {
      // 설정 저장을 위한 API 호출
      try {
        const response = await fetch(`${process.env.REACT_APP_API_URL}/settings`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            personality: personality,
            name: chatbotName,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          alert(`Error: ${errorData.detail}`);
        } else {
          navigate('/chat', { state: { personality, name: chatbotName } });
        }
      } catch (error) {
        console.error("Error saving settings:", error);
        alert("설정 저장에 실패했습니다.");
      }
    } else {
      alert('모든 항목을 입력해주세요!');
    }
  };

  return (
    <div className={styles.container}>
      {/* 오늘 날짜와 시간 표시 */}
      <div className={styles.dateTime}>
        <strong>{currentDateTime}</strong>
      </div>
      <h2 className={styles.settingsTitle}>Settings</h2>
      <label className={styles.settingslabel}>
        챗봇 이름:
        <input 
          className={styles.settingsinput} 
          type="text" 
          value={chatbotName}
          onChange={(e) => setChatbotName(e.target.value)}
          placeholder="챗봇 이름"
        />
      </label><br/>

      <label className={styles.settingsselectLabel}>
        챗봇 성격:
        <select  className={styles.settingsselect} onChange={(e) => setPersonality(e.target.value)}>
          <option value="">--선택--</option>
          <option value="T">현실적</option>
          <option value="F">감정적</option>
        </select>
      </label>
      <br />
      <br />
      <button className={styles.settingsButton} onClick={handleSave}>채팅 시작</button>
    </div>
  );
}

export default Settings;
