import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";
import { App } from "./App";
import { ConsentBanner } from "./components/Consent";
import "./index.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("#root is missing from index.html");
}

// The prerender wrote the markup; the client hydrates it in place.
hydrateRoot(
  root,
  <StrictMode>
    <App />
  </StrictMode>,
);

// The consent banner is not in the prerendered page at all, so it mounts rather than hydrates.
const consent = document.createElement("div");
document.body.appendChild(consent);
createRoot(consent).render(<ConsentBanner />);
