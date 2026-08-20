/** Turn Gemini's jammed markdown/LaTeX into something we can render. */
export function normalizeBotMarkdown(text: string): string {
  let out = text.replace(/\r\n/g, "\n");
  out = out.replace(/\$\\frac\{([^}]+)\}\{([^}]+)\}\$/g, "$1/$2");
  out = out.replace(/\$([^$\n]+)\$/g, "$1");
  out = out.replace(/__([^_\n]{1,120})__/g, "**$1**");
  out = out.replace(/^#{1,6}\s+/gm, "");
  out = out.replace(/[ \t]*---+[ \t]*/g, "\n\n");
  out = out.replace(/\s*\*{0,2}Correct Answer:\*{0,2}\s*/gi, "\n\n**Correct answer:** ");
  out = out.replace(/\s+([A-D])[.)]\s+/g, "\n- **$1.** ");
  out = out.replace(/(^|\n)\s*([A-D])[.)]\s+/g, "$1- **$2.** ");
  out = out.replace(/\s+(\d{1,2})\.\s+(?=[A-Z])/g, "\n\n$1. ");
  out = out.replace(/ \*(?=\s+\*\*)/g, "\n-");
  out = out.replace(/^\*(?=\s+\*\*)/gm, "-");
  out = out.replace(/\n{3,}/g, "\n\n");
  return out.trim();
}

export function stripMarkdown(text: string): string {
  return normalizeBotMarkdown(text)
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/(^|[^*])\*(?!\s)(.+?)\*/g, "$1$2")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^\s*[-*]\s+/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

export type MarkdownBlock =
  | { type: "p"; text: string }
  | { type: "ul"; items: string[] }
  | { type: "ol"; items: string[] };

export function parseMarkdownBlocks(text: string): MarkdownBlock[] {
  const lines = normalizeBotMarkdown(text).split("\n");
  const blocks: MarkdownBlock[] = [];
  let paragraph: string[] = [];
  let bullets: string[] | null = null;
  let numbers: string[] | null = null;

  const flushParagraph = () => {
    if (paragraph.length === 0) return;
    blocks.push({ type: "p", text: paragraph.join(" ").trim() });
    paragraph = [];
  };
  const flushBullets = () => {
    if (bullets?.length) blocks.push({ type: "ul", items: bullets });
    bullets = null;
  };
  const flushNumbers = () => {
    if (numbers?.length) blocks.push({ type: "ol", items: numbers });
    numbers = null;
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      flushParagraph();
      flushBullets();
      flushNumbers();
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.+)$/);
    const numbered = line.match(/^\d+[.)]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      flushNumbers();
      bullets = bullets ?? [];
      bullets.push(bullet[1]);
      continue;
    }
    if (numbered) {
      flushParagraph();
      flushBullets();
      numbers = numbers ?? [];
      numbers.push(numbered[1]);
      continue;
    }
    flushBullets();
    flushNumbers();
    paragraph.push(line);
  }
  flushParagraph();
  flushBullets();
  flushNumbers();
  return blocks;
}
