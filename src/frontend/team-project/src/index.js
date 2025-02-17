import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';  // BrowserRouter는 한 번만 사용
import { GoogleOAuthProvider } from "@react-oauth/google";
import App from './App';

const CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;

// createRoot 방식으로 변경
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <BrowserRouter> {/* Router는 한번만 사용 */}
    <GoogleOAuthProvider clientId={CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </BrowserRouter>
);
