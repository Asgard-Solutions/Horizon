import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/sora";
import "@fontsource-variable/inter";
import "./theme/horizon.theme.css";
import "./styles.css";
import "./home/home.css";
import "./detail/detail.css";
import "./player/player.css";
import App from "./App";
import { startUiScale } from "./theme/uiScale";

startUiScale();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
