import { useEffect, useRef, useState, useCallback } from "react";

interface ChatMessage { role: "user" | "assistant"; content: string; }

export function useChat(conversationId: string, token: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/${conversationId}?token=${token}`);
    ws.onopen = () => setConnected(true);
    ws.onclose = () => { setConnected(false); setTimeout(connect, 3000); };
    ws.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "stream_start") {
        setIsStreaming(true);
        setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
      } else if (data.type === "stream_chunk") {
        setMessages((prev) => {
          const msgs = [...prev];
          msgs[msgs.length - 1].content += data.content;
          return msgs;
        });
      } else if (data.type === "stream_end") {
        setIsStreaming(false);
      }
    };
    wsRef.current = ws;
  }, [conversationId, token]);

  useEffect(() => { connect(); return () => wsRef.current?.close(); }, [connect]);

  const send = (content: string) => {
    setMessages((prev) => [...prev, { role: "user", content }]);
    wsRef.current?.send(JSON.stringify({ content }));
  };

  return { messages, isStreaming, connected, send };
}
