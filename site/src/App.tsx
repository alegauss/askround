import { useEffect } from "react";
import { Footer, Nav } from "./components/Chrome";
import { Agents, Cost, Hero, How, Install, Round, Self } from "./components/Sections";

// The page between the design system's nav and footer is askround's own: the hero with an
// agent's session, a real recorded round, what a round reports, the agent-first design,
// install, the measured cost, and askround measured on itself.
export function App() {
  // Elements marked .reveal rise into place as they scroll in. This only toggles a class on
  // the element itself; it never scrolls the window. With no observer, everything shows.
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>(".reveal"));
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12 },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Round />
        <How />
        <Agents />
        <Install />
        <Cost />
        <Self />
      </main>
      <Footer />
    </>
  );
}
