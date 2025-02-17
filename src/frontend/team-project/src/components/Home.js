import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import styles from "../css/Home.module.css";
import { GoogleLogin } from "@react-oauth/google";

function Home() {
  const navigate = useNavigate();
  const [currentDateTime, setCurrentDateTime] = useState("");

  useEffect(() => {
    const getCurrentDateTime = () => {
      const now = new Date();
      return now.toLocaleString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        weekday: "long",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    };

    const interval = setInterval(() => setCurrentDateTime(getCurrentDateTime()), 1000);
    setCurrentDateTime(getCurrentDateTime());
    return () => clearInterval(interval);
  }, []);

  const handleLoginSuccess = (response) => {
    console.log("Google 로그인 성공:", response);
    const id_token = response.credential;

    fetch("/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token }),
    })
      .then((res) => res.json())
      .then((data) => {
        console.log("User Info:", data);
        navigate("/profile");
      })
      .catch((error) => console.error("로그인 오류:", error));
  };

  const handleLoginFailure = (error) => {
    console.error("Google 로그인 실패:", error);
  };

  return (
    <div className={styles.homeContainer}>
      <div className={styles.homeDatetime}><strong>{currentDateTime}</strong></div>
      <h1 className={styles.homeTitle}>Welcome to Chatbot</h1>
      <button className={styles.homeButton} onClick={() => navigate("/settings")}>시작하기</button>

      {/* Google 로그인 버튼 */}
      <div className="google-login-container">
        <GoogleLogin onSuccess={handleLoginSuccess} onError={handleLoginFailure} />
      </div>
    </div>
  );
}

export default Home;
