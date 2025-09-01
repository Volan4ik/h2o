import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

const tg = (window as any).Telegram?.WebApp;
tg?.ready();
tg?.expand();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
