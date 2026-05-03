import { useChat } from "../hooks/useChat";

interface Props { conversationId: string; token: string; }

export function ChatWindow({ conversationId, token }: Props) {
  const { messages, isStreaming, connected, send } = useChat(conversationId, token);

  return (
    <div className="flex flex-col h-full bg-white rounded-xl shadow">
      <div className="flex items-center gap-2 px-4 py-2 border-b text-xs text-gray-500">
        <span className={`w-2 h-2 rounded-full ${connected ? "bg-green-400" : "bg-red-400"}`} />
        {connected ? "Connected" : "Reconnecting..."}
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[75%] px-4 py-2 rounded-2xl text-sm ${
              m.role === "user" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-800"}`}>
              {m.content}
            </div>
          </div>
        ))}
        {isStreaming && <div className="text-gray-400 text-sm animate-pulse">Thinking...</div>}
      </div>
      <form className="p-3 border-t flex gap-2" onSubmit={(e) => {
        e.preventDefault();
        const input = (e.currentTarget.elements.namedItem("msg") as HTMLInputElement);
        if (input.value.trim()) { send(input.value.trim()); input.value = ""; }
      }}>
        <input name="msg" className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Ask about your tickets..." />
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">Send</button>
      </form>
    </div>
  );
}
