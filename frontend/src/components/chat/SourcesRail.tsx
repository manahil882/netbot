"use client";

import type { Source } from "@/lib/data";
import type { IndexedDocument } from "@/lib/api/chat";

type Props = {
  sources: Source[];
  files: IndexedDocument[];
  highlightedId: string | null;
  onSelect: (source: Source) => void;
  onDeleteFile: (filename: string) => void;
};

export default function SourcesRail({
  sources,
  files,
  highlightedId,
  onSelect,
  onDeleteFile,
}: Props) {
  return (
    <aside className="rail">
      <h5>Files in this chat</h5>
      {files.length === 0 ? (
        <p className="rail-empty">Attach a PDF, Word, or TXT file to ground answers here.</p>
      ) : (
        <ul className="rail-files">
          {files.map((file) => (
            <li key={file.filename} className="rail-file">
              <div>
                <b>{file.filename}</b>
                <small>
                  {file.chunks} chunks · {file.pages} page{file.pages === 1 ? "" : "s"}
                </small>
              </div>
              <button
                type="button"
                className="rail-file-del"
                aria-label={`Remove ${file.filename}`}
                title="Remove from this chat"
                onClick={() => onDeleteFile(file.filename)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      <h5>Sources for this answer</h5>
      {sources.length === 0 ? (
        <p className="rail-empty">Passages used for the latest reply will show here.</p>
      ) : (
        sources.map((source) => (
          <button
            key={source.id}
            type="button"
            className="src-card"
            onClick={() => onSelect(source)}
            style={
              highlightedId === source.id
                ? { borderColor: "var(--navy)", boxShadow: "0 0 0 3px var(--ice)" }
                : undefined
            }
          >
            <span className="tag">{source.tag}</span>
            <b>{source.title}</b>
            <p>{source.blurb}</p>
            <span className="src-meta">
              <span>{source.meta}</span>
              <span>{source.match}% match</span>
            </span>
            <span className="relevance">
              <i style={{ width: `${source.match}%` }} />
            </span>
          </button>
        ))
      )}
    </aside>
  );
}
