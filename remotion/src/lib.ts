import data from "./segments.json";

export const FPS = 30;

export type Seg = { id: string; text: string; title?: string; image?: string; start: number; end: number };
type Data = { total: number; display?: Record<string, string>; segments: Seg[] };

export const SEGS = (data as Data).segments;
export const TOTAL = (data as Data).total;

const PUNCT = /[，。、,.!！？?；;：:“”"「」]/g;
const DISPLAY = Object.entries((data as Data).display ?? {});

/** The script keeps numbers in spoken form for the TTS; subtitles show digits. */
const display = (t: string) => DISPLAY.reduce((s, [from, to]) => s.split(from).join(to), t);

/** Subtitle chunks: split each line at punctuation, timed by its share of spoken characters. */
export type Chunk = { text: string; from: number; to: number };
export const CHUNKS: Chunk[] = SEGS.flatMap((s) => {
  const parts = s.text.split(/(?<=[，。、！？；：,!?;:])/).map((p) => p.replace(PUNCT, " ").trim()).filter(Boolean);
  const len = (t: string) => t.replace(/\s/g, "").length;
  const total = parts.reduce((a, p) => a + len(p), 0);
  let t = s.start;
  return parts.map((p) => {
    const d = ((s.end - s.start) * len(p)) / total;
    const c = { text: display(p), from: t, to: t + d };
    t += d;
    return c;
  });
});
