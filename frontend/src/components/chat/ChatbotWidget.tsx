import React, { useState, useEffect, useRef } from "react";
import {
  Bot,
  Send,
  X,
  Sparkles,
  Maximize2,
  Minimize2,
  RotateCcw,
  Check,
  Copy,
  Globe,
  TrendingUp,
  Package,
  Layers,
  ArrowLeftRight,
  HelpCircle,
  KeyRound,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { chatAPI, ChatMessage, ChatStatus } from "@/services/api";
import { MarkdownMessage } from "./MarkdownMessage";
import { Button } from "@/components/ui/button";

interface ChatbotWidgetProps {
  isOpen?: boolean;
  setIsOpen?: (open: boolean) => void;
  showFloatingButton?: boolean;
}

const INITIAL_GREETING: ChatMessage = {
  id: "msg-welcome",
  role: "assistant",
  content: `Hello! I am **Stocker AI Copilot**, your real-time supply chain, inventory, and forecasting intelligence partner.

I have direct access to your live network data and can help with:
- ⚠️ **Stockout & Low Stock Alerts**: Instant status of critical SKUs below ROP.
- 🔄 **Inter-Store Balancing**: Automated store-to-store transfer recommendations.
- 🛒 **Procurement & Lead Times**: Supplier deadlines and "order-by" directives.
- 📈 **ML Demand Forecasting**: Explaining Facebook Prophet and Croston's algorithm.
- 📐 **Cost Optimization**: Dynamic EOQ, Safety Stock, and Reorder Point calculations.

🌐 **Universal Language Support**: You can ask me in **English, हिन्दी, मराठी, Hinglish**, or any language!`,
  provider: "Stocker AI",
  timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
};

const SUGGESTIONS = [
  { label: "⚠️ Low Stock Alert", query: "Which products are currently low on stock?", icon: Package },
  { label: "🔄 Inter-Store Transfers", query: "Show recommended inter-store transfers to balance inventory.", icon: ArrowLeftRight },
  { label: "🛒 Procurement Directives", query: "What purchase orders need to be placed based on supplier lead times?", icon: Layers },
  { label: "📈 Croston vs Prophet", query: "Explain how Croston's method works for intermittent demand versus Prophet.", icon: TrendingUp },
  { label: "📐 Explain EOQ Formula", query: "How is Economic Order Quantity (EOQ) and Reorder Point (ROP) calculated in Stocker?", icon: HelpCircle },
  { label: "🇮🇳 हिन्दी में जानकारी", query: "स्टॉकर क्या है और यह इन्वेंटरी लागत कैसे कम करता है?", icon: Globe },
  { label: "🚩 मराठीत सांगा", query: "स्टॉकर प्रोजेक्ट काय करतो आणि स्टोअर्स मधील माल कसा हलवला जातो?", icon: Globe },
];

export const ChatbotWidget: React.FC<ChatbotWidgetProps> = ({
  isOpen: controlledIsOpen,
  setIsOpen: controlledSetIsOpen,
  showFloatingButton = false,
}) => {
  const [internalIsOpen, setInternalIsOpen] = useState(false);
  const isChatOpen = controlledIsOpen !== undefined ? controlledIsOpen : internalIsOpen;
  const setChatOpen = controlledSetIsOpen !== undefined ? controlledSetIsOpen : setInternalIsOpen;

  // Handle ESC key to close chat
  useEffect(() => {
    if (!isChatOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setChatOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isChatOpen, setChatOpen]);

  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = localStorage.getItem("stocker_chat_history");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch {
        // Fallback to initial
      }
    }
    return [INITIAL_GREETING];
  });

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [status, setStatus] = useState<ChatStatus | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [customGeminiKey, setCustomGeminiKey] = useState(() => localStorage.getItem("stocker_gemini_key") || "");
  const [tempKeyInput, setTempKeyInput] = useState(customGeminiKey);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isChatOpen) {
      scrollToBottom();
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isChatOpen, messages, loading]);

  // Persist messages in localStorage
  useEffect(() => {
    localStorage.setItem("stocker_chat_history", JSON.stringify(messages.slice(-20)));
  }, [messages]);

  // Fetch status on mount
  useEffect(() => {
    chatAPI
      .getStatus()
      .then((res) => {
        if (res.success) setStatus(res.data);
      })
      .catch(() => {
        // Silent fallback
      });
  }, []);

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend ?? input).trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // Build history for context
      const historyPayload = messages
        .filter((m) => m.id !== "msg-welcome")
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await chatAPI.sendMessage(text, historyPayload, customGeminiKey);

      if (res.success && res.data) {
        const botMsg: ChatMessage = {
          id: `bot-${Date.now()}`,
          role: "assistant",
          content: res.data.reply,
          provider: res.data.provider,
          model: res.data.model,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        };
        setMessages((prev) => [...prev, botMsg]);
      } else {
        throw new Error("No response data");
      }
    } catch (err: unknown) {
      const errMsg: ChatMessage = {
        id: `bot-err-${Date.now()}`,
        role: "assistant",
        content: `⚠️ **Connection Notice:** Unable to reach AI services right now.
*(Make sure the backend server is running on port 5001 or check your network).*`,
        provider: "Offline System",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const handleClearChat = () => {
    setMessages([INITIAL_GREETING]);
    localStorage.removeItem("stocker_chat_history");
  };

  const handleCopyMessage = (id: string, text: string) => {
    void navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const activeProviderLabel =
    customGeminiKey || status?.active_provider === "gemini"
      ? "Gemini 1.5 Flash"
      : status?.active_provider === "openai"
      ? "OpenAI GPT-4o"
      : "Stocker Live Brain";

  return (
    <>
      {/* Optional Sleek Floating Action Button */}
      {showFloatingButton && !isChatOpen && (
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 350, damping: 25 }}
          className="fixed bottom-6 right-6 z-50"
        >
          <button
            type="button"
            onClick={() => setChatOpen(true)}
            aria-label="Open AI Copilot"
            className="copper-gold-rim group relative flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-r from-emerald-800 via-teal-900 to-emerald-950 text-white shadow-xl shadow-amber-500/15 transition-all duration-300 hover:scale-110 hover:shadow-amber-500/35 focus:outline-none focus:ring-4 focus:ring-amber-400/30 cursor-pointer"
            title="Open Stocker AI Copilot (⌘J)"
          >
            <Bot className="h-5 w-5 text-amber-300 transition-transform group-hover:rotate-12 duration-200" />
            <span className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400" />
            </span>
          </button>
        </motion.div>
      )}

      {/* Slide-out Chat Panel */}
      <AnimatePresence>
        {isChatOpen && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 320, damping: 28 }}
            className={`fixed bottom-4 right-4 z-50 flex flex-col rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-2xl backdrop-blur-xl transition-all duration-300 overflow-hidden ${
              isExpanded
                ? "w-[min(94vw,740px)] h-[min(92vh,820px)]"
                : "w-[min(94vw,430px)] h-[min(88vh,660px)]"
            }`}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[var(--border)] bg-gradient-to-r from-emerald-600/10 via-amber-600/10 to-teal-600/10 px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="copper-gold-rim relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-700 to-teal-900 text-white shadow-md">
                  <Bot className="h-5 w-5 text-amber-300" />
                  <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-amber-400 ring-2 ring-[var(--surface)]" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold silver-text font-mono">STOCKER COPILOT</h3>
                    <span className="copper-gold-badge rounded px-2 py-0.5 text-[10px] font-mono font-medium">
                      {activeProviderLabel}
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--muted)] flex items-center gap-1">
                    <Globe className="h-3 w-3 text-amber-400" />
                    <span>Multilingual • English, हिन्दी, मराठी +</span>
                  </p>
                </div>
              </div>

              {/* Action icons */}
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className={`h-8 w-8 ${showKeyModal ? "text-primary" : "text-[var(--muted)]"} hover:text-[var(--text)]`}
                  onClick={() => {
                    setTempKeyInput(customGeminiKey);
                    setShowKeyModal(!showKeyModal);
                  }}
                  title="Configure Gemini API Key"
                >
                  <KeyRound className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-[var(--muted)] hover:text-[var(--text)]"
                  onClick={() => setIsExpanded(!isExpanded)}
                  title={isExpanded ? "Collapse width" : "Expand width"}
                >
                  {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-[var(--muted)] hover:text-[var(--text)]"
                  onClick={handleClearChat}
                  title="Clear chat history"
                >
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-[var(--muted)] hover:text-[var(--text)]"
                  onClick={() => setChatOpen(false)}
                  title="Close chat"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Optional Gemini API Key Drawer */}
            {showKeyModal && (
              <div className="border-b border-[var(--border)] bg-[var(--surface2)] p-3 text-xs">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-semibold text-[var(--text)] flex items-center gap-1.5">
                    <KeyRound className="h-3.5 w-3.5 text-primary" /> Google Gemini API Key
                  </span>
                  <a
                    href="https://aistudio.google.com/app/apikey"
                    target="_blank"
                    rel="noreferrer"
                    className="text-[10px] text-primary underline"
                  >
                    Get Free Key ↗
                  </a>
                </div>
                <p className="text-[11px] text-[var(--muted)] mb-2">
                  Optional: Paste your Google Gemini API key to enable open-ended generative AI in any language. Without a key, Stocker uses its built-in live intelligence engine.
                </p>
                <div className="flex gap-1.5">
                  <input
                    type="password"
                    value={tempKeyInput}
                    onChange={(e) => setTempKeyInput(e.target.value)}
                    placeholder="AIzaSy..."
                    className="flex-1 rounded-md border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-xs outline-none focus:border-primary"
                  />
                  <Button
                    size="sm"
                    className="h-7 text-xs px-2.5"
                    onClick={() => {
                      const trimmed = tempKeyInput.trim();
                      setCustomGeminiKey(trimmed);
                      if (trimmed) {
                        localStorage.setItem("stocker_gemini_key", trimmed);
                      } else {
                        localStorage.removeItem("stocker_gemini_key");
                      }
                      setShowKeyModal(false);
                    }}
                  >
                    Save
                  </Button>
                  {customGeminiKey && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs px-2"
                      onClick={() => {
                        setCustomGeminiKey("");
                        setTempKeyInput("");
                        localStorage.removeItem("stocker_gemini_key");
                        setShowKeyModal(false);
                      }}
                    >
                      Remove
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* Quick Suggestion Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto border-b border-[var(--border)] bg-[var(--surface2)]/50 px-3 py-2 text-xs no-scrollbar">
              <span className="text-[10px] uppercase font-bold text-[var(--muted)] shrink-0 flex items-center gap-0.5 mr-1">
                <Sparkles className="h-3 w-3 text-primary" /> Suggestions:
              </span>
              {SUGGESTIONS.map((item, idx) => {
                const IconComponent = item.icon;
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => void handleSend(item.query)}
                    className="flex shrink-0 items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1 text-[11px] text-[var(--text)] hover:border-primary/50 hover:bg-primary/5 transition-all"
                  >
                    <IconComponent className="h-3 w-3 text-primary" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Message Stream */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg) => {
                const isUser = msg.role === "user";
                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
                  >
                    {!isUser && (
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-600 to-teal-700 text-white shadow-sm mt-0.5">
                        <Bot className="h-4 w-4" />
                      </div>
                    )}

                    <div className={`flex flex-col ${isUser ? "items-end" : "items-start"} max-w-[85%]`}>
                      <div
                        className={`rounded-2xl px-4 py-2.5 shadow-sm text-xs ${
                          isUser
                            ? "bg-gradient-to-r from-emerald-600 to-teal-700 text-white rounded-tr-xs"
                            : "bg-[var(--surface2)] text-[var(--text)] border border-[var(--border)] rounded-tl-xs"
                        }`}
                      >
                        {isUser ? (
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        ) : (
                          <MarkdownMessage content={msg.content} />
                        )}
                      </div>

                      {/* Footer info: timestamp & copy */}
                      <div className="mt-1 flex items-center gap-2 px-1 text-[10px] text-[var(--muted)]">
                        <span>{msg.timestamp}</span>
                        {!isUser && (
                          <button
                            type="button"
                            onClick={() => handleCopyMessage(msg.id, msg.content)}
                            className="flex items-center gap-0.5 hover:text-[var(--text)] transition-colors"
                            title="Copy message"
                          >
                            {copiedId === msg.id ? (
                              <Check className="h-3 w-3 text-emerald-500" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                            <span>{copiedId === msg.id ? "Copied" : "Copy"}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </motion.div>
                );
              })}

              {/* Typing loader */}
              {loading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-3 text-xs text-[var(--muted)]"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-600 to-teal-700 text-white">
                    <Bot className="h-4 w-4" />
                  </div>
                  <div className="flex items-center gap-1.5 rounded-2xl bg-[var(--surface2)] border border-[var(--border)] px-4 py-3">
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="h-2 w-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: "300ms" }} />
                    <span className="ml-2 text-[11px] font-medium text-primary">Analyzing supply chain data...</span>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="border-t border-[var(--border)] bg-[var(--surface)] p-3">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void handleSend();
                }}
                className="flex items-end gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface2)] px-3 py-2 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 transition-all"
              >
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything in English, हिन्दी, मराठी... (Shift+Enter for new line)"
                  rows={1}
                  className="max-h-28 flex-1 resize-none bg-transparent text-xs text-[var(--text)] placeholder-[var(--muted)] outline-none"
                  style={{ minHeight: "24px" }}
                />

                <Button
                  type="submit"
                  size="icon"
                  disabled={!input.trim() || loading}
                  className="h-8 w-8 shrink-0 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-700 text-white shadow-sm hover:opacity-95 disabled:opacity-40"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </form>

              <div className="mt-2 flex items-center justify-between px-1 text-[10px] text-[var(--muted)]">
                <span className="flex items-center gap-1">
                  <Sparkles className="h-3 w-3 text-amber-500" />
                  <span>Press <strong>Enter</strong> to send, <strong>Shift+Enter</strong> for newline</span>
                </span>
                <span>Stocker Intelligence v2.0</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
