import { Footer, Nav } from "./components/Chrome";
import { Agents, Cost, How, Install, Intro, Round } from "./components/Sections";

// The page between the design system's nav and footer is askround's own: the pain and the
// promise, a real recorded round, what a round reports, the agent-first design, install and
// the measured cost.
export function App() {
  return (
    <>
      <Nav />
      <main>
        <Intro />
        <Round />
        <How />
        <Agents />
        <Install />
        <Cost />
      </main>
      <Footer />
    </>
  );
}
