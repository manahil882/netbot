import type { ReactNode } from "react";
import { parseMarkdownBlocks } from "@/lib/markdown";

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|`[^`]+`)/g);
  return parts.map((part, index) => {
    const key = `${keyPrefix}-${index}`;
    if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      return <code key={key}>{part.slice(1, -1)}</code>;
    }
    return part ? <span key={key}>{part}</span> : null;
  });
}

export default function MarkdownBody({ text }: { text: string }) {
  const blocks = parseMarkdownBlocks(text);

  return (
    <div className="bubble-md">
      {blocks.map((block, index) => {
        if (block.type === "ul" || block.type === "ol") {
          const List = block.type === "ul" ? "ul" : "ol";
          return (
            <List key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInline(item, `${index}-${itemIndex}`)}</li>
              ))}
            </List>
          );
        }
        return <p key={index}>{renderInline(block.text, String(index))}</p>;
      })}
    </div>
  );
}
