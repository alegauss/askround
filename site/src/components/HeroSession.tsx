import { useEffect, useRef } from "react";
import { SiteRich as Rich } from "@viglet/viglet-design-system/site";
import { session } from "../content";

// The hero is a session, after FreeHarbor's: the agent's task and the three calls it makes.
// Every step renders on the server and with no JavaScript, so a crawler and an assistant read
// it whole; after mount the steps are revealed one at a time. The panel scrolls its own
// element as each lands, never the window, so a reader who has scrolled on is not pulled back.
export function HeroSession() {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const panel = panelRef.current;
    if (!panel) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const steps = Array.from(panel.querySelectorAll<HTMLElement>(".session-step"));
    if (steps.length === 0) return;

    panel.classList.add("session--playing");
    let i = 0;
    let timer = 0;
    const tick = () => {
      if (i >= steps.length) return;
      steps[i].classList.add("in");
      panel.scrollTop = panel.scrollHeight;
      i += 1;
      timer = window.setTimeout(tick, 1400);
    };
    timer = window.setTimeout(tick, 500);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <>
      <div className="session-eyebrow">{session.eyebrow}</div>
      <div className="session reveal">
        <div className="session-ask">
          <span className="session-ask-tag">Task</span>
          <span className="session-ask-text">{session.task}</span>
        </div>
        <div className="session-scroll" ref={panelRef}>
          {session.steps.map((step) => (
            <div className="session-step" key={step.cmd}>
              <div className="session-cmd">
                <span className="session-prompt" aria-hidden="true">
                  ›
                </span>
                <code>{step.cmd}</code>
                <span className="session-cost">{step.cost}</span>
              </div>
              {"pack" in step && step.pack ? (
                <pre className="session-out session-pack">{step.pack.join("\n")}</pre>
              ) : (
                <div className="session-out">{"out" in step ? step.out : ""}</div>
              )}
            </div>
          ))}
        </div>
        <div className="session-foot">
          <span className="session-cmp today">{session.today}</span>
          <span className="session-cmp target">{session.target}</span>
        </div>
      </div>
      <p className="session-note">
        <Rich runs={session.note} />
      </p>
    </>
  );
}
