import { useEffect, useState } from "react";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { ChatWindow } from "../components/ChatWindow";
import { conversationsApi } from "../lib/api";

interface Conversation { id: string; created_at: string; }

export function ChatPage() {
  const token = localStorage.getItem("access_token") ?? "";
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);

  useEffect(() => {
    conversationsApi.list().then((res) => {
      setConversations(res.data);
      if (res.data.length > 0) setActiveId(res.data[0].id);
    });
  }, []);

  const createNew = async () => {
    const res = await conversationsApi.create();
    setConversations((prev) => [res.data, ...prev]);
    setActiveId(res.data.id);
  };

  const deleteConversation = async (id: string) => {
    await conversationsApi.delete(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
    if (activeId === id) setActiveId(conversations[1]?.id ?? null);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-64 flex flex-col bg-white border-r p-3 gap-2">
        <button onClick={createNew}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700">
          <Plus size={14} /> New Conversation
        </button>
        <div className="flex-1 overflow-y-auto space-y-1">
          {conversations.map((c) => (
            <div key={c.id}
              className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm group ${
                activeId === c.id ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-600 hover:bg-gray-50"}`}
              onClick={() => setActiveId(c.id)}>
              <span className="flex items-center gap-2 truncate">
                <MessageSquare size={13} />
                <span className="truncate">{new Date(c.created_at).toLocaleDateString()}</span>
              </span>
              <button className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500"
                onClick={(e) => { e.stopPropagation(); deleteConversation(c.id); }}>
                <Trash2 size={13} />
              </button>
            </div>
          ))}
        </div>
      </aside>
      <main className="flex-1 p-4">
        {activeId ? <ChatWindow conversationId={activeId} token={token} /> :
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Create a new conversation to get started.
          </div>}
      </main>
    </div>
  );
}
