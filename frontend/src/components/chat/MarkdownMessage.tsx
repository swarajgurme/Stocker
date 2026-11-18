import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check, Copy, ExternalLink } from "lucide-react";

interface MarkdownMessageProps {
  content: string;
}

export const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content }) => {
  const navigate = useNavigate();

  // Helper to render inline elements (bold, italic, code, links, math)
  const renderInline = (text: string) => {
    // Regex for links [text](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
    const parts: (string | React.ReactNode)[] = [];
    let lastIndex = 0;
    let match: RegExpExecArray | null;

    while ((match = linkRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(parseFormatting(text.slice(lastIndex, match.index)));
      }
      const label = match[1];
      const url = match[2];

      // If internal route (starts with /), make it an interactive route button
      if (url.startsWith("/")) {
        parts.push(
          <button
            key={match.index}
            type="button"
            onClick={() => navigate(url)}
            className="inline-flex items-center gap-1 font-semibold text-primary underline underline-offset-2 hover:opacity-80 transition-opacity"
          >
            <span>{label}</span>
            <ExternalLink className="h-3 w-3" />
          </button>
        );
      } else {
        parts.push(
          <a
            key={match.index}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 font-semibold text-primary underline underline-offset-2 hover:opacity-80 transition-opacity"
          >
            <span>{label}</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        );
      }
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      parts.push(parseFormatting(text.slice(lastIndex)));
    }

    return parts.length > 0 ? parts : parseFormatting(text);
  };

  const parseFormatting = (str: string): React.ReactNode => {
    // Split tokens by code, bold, italic
    // We can do standard replacement
    const elements: (string | React.ReactNode)[] = [];

    // Pattern for inline code, bold, italic
    const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\$[^$]+\$)/g;
    let m: RegExpExecArray | null;
    let lastPos = 0;

    while ((m = regex.exec(str)) !== null) {
      if (m.index > lastPos) {
        elements.push(str.substring(lastPos, m.index));
      }
      const token = m[0];
      if (token.startsWith("`") && token.endsWith("`")) {
        elements.push(
          <code
            key={m.index}
            className="rounded bg-[var(--surface2)] px-1.5 py-0.5 font-mono text-[11px] font-medium text-primary border border-[var(--border)]"
          >
            {token.slice(1, -1)}
          </code>
        );
      } else if (token.startsWith("**") && token.endsWith("**")) {
        elements.push(
          <strong key={m.index} className="font-semibold text-[var(--text)]">
            {token.slice(2, -2)}
          </strong>
        );
      } else if (token.startsWith("*") && token.endsWith("*")) {
        elements.push(
          <em key={m.index} className="italic text-[var(--text)]">
            {token.slice(1, -1)}
          </em>
        );
      } else if (token.startsWith("$") && token.endsWith("$")) {
        elements.push(
          <span
            key={m.index}
            className="font-mono text-xs font-semibold text-amber-500 dark:text-amber-400 bg-amber-500/10 px-1 py-0.5 rounded"
          >
            {token.slice(1, -1)}
          </span>
        );
      }
      lastPos = m.index + token.length;
    }

    if (lastPos < str.length) {
      elements.push(str.substring(lastPos));
    }

    return elements.length > 0 ? elements : str;
  };

  // Split content by code blocks vs text
  const lines = content.split("\n");
  const renderedElements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBuffer: string[] = [];
  let codeLang = "";
  let tableBuffer: string[] = [];

  const flushTable = (key: number) => {
    if (tableBuffer.length === 0) return null;
    const rows = tableBuffer.map((r) =>
      r
        .split("|")
        .slice(1, -1)
        .map((cell) => cell.trim())
    );
    tableBuffer = [];

    if (rows.length < 2) return null;

    const headers = rows[0];
    const dataRows = rows.slice(2); // Skip separator row (---|---|---)

    return (
      <div key={`table-${key}`} className="my-2.5 overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-[var(--surface2)] text-[var(--text)] font-semibold border-b border-[var(--border)]">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className="px-3 py-2 border-r last:border-r-0 border-[var(--border)]">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {dataRows.map((row, ri) => (
              <tr key={ri} className="hover:bg-[var(--surface2)]/50 transition-colors">
                {row.map((cell, ci) => (
                  <td key={ci} className="px-3 py-1.5 border-r last:border-r-0 border-[var(--border)]">
                    {renderInline(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block delimiters
    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        // End of code block
        const codeText = codeBuffer.join("\n");
        renderedElements.push(
          <CodeBlock key={`code-${i}`} code={codeText} language={codeLang} />
        );
        codeBuffer = [];
        codeLang = "";
        inCodeBlock = false;
      } else {
        // Start of code block
        if (tableBuffer.length > 0) {
          const t = flushTable(i);
          if (t) renderedElements.push(t);
        }
        inCodeBlock = true;
        codeLang = line.trim().slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    // Markdown Table
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      tableBuffer.push(line.trim());
      continue;
    } else if (tableBuffer.length > 0) {
      const t = flushTable(i);
      if (t) renderedElements.push(t);
    }

    // Headers
    if (line.startsWith("### ")) {
      renderedElements.push(
        <h3 key={i} className="mt-3 mb-1 text-sm font-bold text-[var(--text)] flex items-center gap-1.5">
          {renderInline(line.replace("### ", ""))}
        </h3>
      );
      continue;
    }
    if (line.startsWith("#### ")) {
      renderedElements.push(
        <h4 key={i} className="mt-2 mb-1 text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
          {renderInline(line.replace("#### ", ""))}
        </h4>
      );
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      renderedElements.push(
        <blockquote
          key={i}
          className="my-1.5 border-l-2 border-primary/60 bg-primary/5 pl-2.5 py-1 text-xs italic text-[var(--muted)] rounded-r"
        >
          {renderInline(line.replace("> ", ""))}
        </blockquote>
      );
      continue;
    }

    // Math display formula $$...$$
    if (line.trim().startsWith("$$") && line.trim().endsWith("$$")) {
      renderedElements.push(
        <div
          key={i}
          className="my-2 rounded-md bg-[var(--surface2)]/80 border border-[var(--border)] px-3 py-2 text-center font-mono text-xs text-primary font-bold overflow-x-auto"
        >
          {line.trim().slice(2, -2).trim()}
        </div>
      );
      continue;
    }

    // Unordered List
    if (line.trim().startsWith("- ") || line.trim().startsWith("• ") || line.trim().startsWith("* ")) {
      const listContent = line.trim().replace(/^[-•*]\s+/, "");
      renderedElements.push(
        <li key={i} className="ml-4 list-disc text-xs leading-relaxed text-[var(--text)] my-0.5">
          {renderInline(listContent)}
        </li>
      );
      continue;
    }

    // Numbered List
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      renderedElements.push(
        <li key={i} className="ml-4 list-decimal text-xs leading-relaxed text-[var(--text)] my-0.5">
          {renderInline(numMatch[2])}
        </li>
      );
      continue;
    }

    // Empty line
    if (!line.trim()) {
      renderedElements.push(<div key={i} className="h-1.5" />);
      continue;
    }

    // Regular paragraph
    renderedElements.push(
      <p key={i} className="text-xs leading-relaxed text-[var(--text)] my-1">
        {renderInline(line)}
      </p>
    );
  }

  if (tableBuffer.length > 0) {
    const t = flushTable(lines.length);
    if (t) renderedElements.push(t);
  }

  return <div className="space-y-0.5 select-text break-words">{renderedElements}</div>;
};

const CodeBlock: React.FC<{ code: string; language?: string }> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-2 rounded-md border border-[var(--border)] bg-zinc-950 text-zinc-100 overflow-hidden font-mono text-xs">
      <div className="flex items-center justify-between bg-zinc-900/80 px-3 py-1 text-[10px] text-zinc-400 border-b border-zinc-800">
        <span>{language || "code"}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-white transition-colors"
          title="Copy code"
        >
          {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
          <span>{copied ? "Copied" : "Copy"}</span>
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-[11px] leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
};
