import { useAds } from "./ads";

/**
 * One house ad slot, from japode-ads. The container is prerendered empty: the loader
 * attaches a shadow root to it and draws inside, so this stylesheet cannot reach the banner
 * and the banner cannot leak into the page. Its box is reserved in index.css at the height the
 * loader reserves, so nothing moves when it arrives; with no catalogue the loader collapses it.
 */
export function Ad({ slot }: Readonly<{ slot: string }>) {
  useAds();
  return (
    <div className="ad-band">
      <div className="vg-site-wrap">
        <div
          className="ad"
          data-japode-ads=""
          data-ad-format="in-content"
          data-ad-slot={slot}
          // the loader then keeps no recency memory in localStorage
          data-ad-memory="off"
          // the catalogue's askround campaign points at the repository, not this domain
          data-ad-exclude="askround"
        />
      </div>
    </div>
  );
}
