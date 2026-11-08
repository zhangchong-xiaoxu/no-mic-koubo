import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CHUNKS, FPS, SEGS, Seg } from "./lib";

const C = { bg: "#0B0C10", card: "#1B1E25", ink: "#F5F2EC", sub: "#9BA3AF", accent: "#FF8A2B" };
const FONT = '"Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif';

/** One line of narration: big title on top, optional real screenshot below. Edit freely. */
const Scene: React.FC<{ seg: Seg }> = ({ seg }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 18, mass: 0.6 } });
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 60, padding: "220px 80px 520px" }}>
      {seg.title && (
        <div style={{ fontFamily: FONT, fontWeight: 900, fontSize: 112, lineHeight: 1.15, color: C.ink, textAlign: "center",
          transform: `translateY(${interpolate(pop, [0, 1], [40, 0])}px)`, opacity: pop }}>
          {seg.title}
        </div>
      )}
      {seg.image && (
        <Img src={staticFile(seg.image)} style={{ maxWidth: "100%", maxHeight: 900, objectFit: "contain", borderRadius: 24,
          border: `2px solid ${C.card}`, boxShadow: "0 30px 80px rgba(0,0,0,0.5)", transform: `scale(${interpolate(pop, [0, 1], [0.94, 1])})` }} />
      )}
    </AbsoluteFill>
  );
};

const Subtitles: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  const c = CHUNKS.find((x) => t >= x.from && t < x.to);
  if (!c) return null;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 360 }}>
      <div style={{ fontFamily: FONT, fontWeight: 700, fontSize: 60, color: C.ink, background: "rgba(0,0,0,0.55)",
        padding: "14px 32px", borderRadius: 16, maxWidth: 940, textAlign: "center" }}>
        {c.text}
      </div>
    </AbsoluteFill>
  );
};

/** China's AIGC labeling rules (2025-09-01) require marking synthetic voices; keep this tag. */
const AigcTag: React.FC = () => (
  <div style={{ position: "absolute", left: 48, top: 64, fontFamily: FONT, fontSize: 30, color: C.sub,
    border: `2px solid ${C.sub}`, borderRadius: 10, padding: "6px 14px" }}>
    配音：AI 合成
  </div>
);

export const Main: React.FC = () => (
  <AbsoluteFill style={{ background: C.bg }}>
    {SEGS.map((s, i) => {
      const from = Math.round((i === 0 ? 0 : s.start) * FPS);
      const next = SEGS[i + 1];
      const to = next ? Math.round(next.start * FPS) : Math.ceil((s.end + 1) * FPS);
      return (
        <Sequence key={s.id} from={from} durationInFrames={Math.max(1, to - from)}>
          <Scene seg={s} />
        </Sequence>
      );
    })}
    <Subtitles />
    <AigcTag />
    <Audio src={staticFile("narration.wav")} />
  </AbsoluteFill>
);
