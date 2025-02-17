import React from 'react';
import { Routes, Route } from 'react-router-dom';  // Router 한번만 사용
import Settings from './components/Settings';
import Chat from './components/Chat';
import Home from './components/Home';  // 홈 컴포넌트 추가

function App() {
  return (
    <Routes>  {/* Router는 한 번만 사용 */}
      <Route path="/" element={<Home />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/chat" element={<Chat />} />
    </Routes>
  );
}

export default App;
