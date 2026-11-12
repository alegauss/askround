import { StrictMode } from "react";
import { hydrateRoot } from "react-dom/client";
import { App } from "./App";
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
