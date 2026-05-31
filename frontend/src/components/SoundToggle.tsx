import { useSim } from "../store/useSim";

export function SoundToggle({ withLabel = false }: { withLabel?: boolean }) {
  const muted = useSim((s) => s.muted);
  const toggleMuted = useSim((s) => s.toggleMuted);
  return (
    <button
      onClick={toggleMuted}
      aria-pressed={!muted}
      title={muted ? "Sound off — click to enable" : "Sound on"}
      className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-semibold uppercase tracking-widest transition ${
        muted ? "border-line text-muted hover:border-brand" : "border-accent bg-accent/10 text-accent"
      }`}
    >
      <svg
        viewBox="0 0 24 24"
        className="h-4 w-4"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M11 5 6 9H3v6h3l5 4V5Z" fill="currentColor" stroke="none" />
        {muted ? (
          <path d="M16 9l5 6M21 9l-5 6" />
        ) : (
          <>
            <path d="M15.5 8.5a5 5 0 0 1 0 7" />
            <path d="M18.5 6a8 8 0 0 1 0 12" />
          </>
        )}
      </svg>
      {withLabel && <span>{muted ? "Sound off" : "Sound on"}</span>}
    </button>
  );
}
