// The motion behind the hero and the footer: one question sent out, answers coming back.
// Rings leave the centre and fade as they widen, each a quarter of the cycle behind the last,
// so the field is never empty and never crowded; four dots ride an orbit, the four assistants.
//
// Decorative only: no copy, hidden from the accessibility tree, and still under
// prefers-reduced-motion (index.css). Every animation is a transform or an opacity on its own
// element, so nothing on the page reflows. `quiet` is the footer's: fewer rings, no orbit.

const RINGS = [0, 1, 2, 3];
const ASSISTANTS = [0, 1, 2, 3];

export function Ripples({ quiet = false }: Readonly<{ quiet?: boolean }>) {
  return (
    <div className={quiet ? "ripples ripples--quiet" : "ripples"} aria-hidden="true">
      {RINGS.slice(0, quiet ? 2 : 4).map((i) => (
        <span className="ripple" key={i} style={{ animationDelay: `${i * -2}s` }} />
      ))}
      {!quiet && (
        <div className="orbit">
          {ASSISTANTS.map((i) => (
            <span className={`orbit-dot orbit-dot-${i}`} key={i} />
          ))}
        </div>
      )}
    </div>
  );
}
