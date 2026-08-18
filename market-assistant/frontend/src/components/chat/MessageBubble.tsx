import { DISCLAIMER_TEXT } from "../Disclaimer";
import { MiniChart } from "./MiniChart";
import { ToolActivityIndicator } from "./ToolActivityIndicator";
import type { ChatMessageVM } from "../../stores/chatStore";

// Only real trading pairs (a base ticker over a known quote asset). The old
// broad `[A-Z]{2,5}/[A-Z]{2,6}` matched indicator text like "EMA/VWAP" and
// spuriously rendered a mini-chart for a non-existent symbol.
const SYMBOL_RE = /\b[A-Z]{2,5}\/(?:USDT|USDC|USD|BUSD|BTC|ETH|EUR|GBP|JPY|INR)\b/;

/** An assistant reply that reads as a recommendation carries the disclaimer.
 * The server-side advice guard already enforces this on persisted answers; the
 * bubble just surfaces it as a footer (and never adds imperative framing). */
function isRecommendation(content: string): boolean {
  return content.includes(DISCLAIMER_TEXT);
}

export function MessageBubble({ message }: { message: ChatMessageVM }) {
  const body = message.content.replace(DISCLAIMER_TEXT, "").trim();
  const isAssistant = message.role === "assistant";
  const showDisclaimer = isAssistant && isRecommendation(message.content);
  const symbol = isAssistant ? message.content.match(SYMBOL_RE)?.[0] : undefined;

  return (
    <div className={`chat-bubble chat-bubble--${message.role}`}>
      {message.toolEvents && message.toolEvents.length > 0 && (
        <div className="tool-activity-row">
          {message.toolEvents.map((e, i) => (
            <ToolActivityIndicator key={i} event={e} />
          ))}
        </div>
      )}
      <p className="chat-bubble-body">{body}</p>
      {symbol && <MiniChart symbol={symbol} />}
      {showDisclaimer && <p className="chat-bubble-disclaimer">{DISCLAIMER_TEXT}</p>}
    </div>
  );
}
