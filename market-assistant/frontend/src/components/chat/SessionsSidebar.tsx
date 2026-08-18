import { useChatStore } from "../../stores/chatStore";

interface SessionsSidebarProps {
  onSelect: (id: string) => void;
  onNew: () => void;
}

function label(createdAt: string): string {
  const d = new Date(createdAt);
  return Number.isNaN(d.getTime()) ? "New chat" : d.toLocaleString();
}

export function SessionsSidebar({ onSelect, onNew }: SessionsSidebarProps) {
  const sessions = useChatStore((s) => s.sessions);
  const activeSessionId = useChatStore((s) => s.activeSessionId);

  return (
    <aside className="sessions-sidebar panel" aria-label="Chat sessions">
      <header className="panel-h">
        <h3>Sessions</h3>
        <button type="button" className="sessions-new" onClick={onNew}>
          New
        </button>
      </header>
      <div className="sessions-list">
        {sessions.length === 0 && <p className="sessions-empty">No saved chats yet.</p>}
        {sessions.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`session-item${s.id === activeSessionId ? " session-item--active" : ""}`}
            onClick={() => onSelect(s.id)}
          >
            {label(s.createdAt)}
          </button>
        ))}
      </div>
    </aside>
  );
}
