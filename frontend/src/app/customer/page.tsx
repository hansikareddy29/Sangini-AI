"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Send, Clock, Package, CheckCircle2 } from "lucide-react";
import { format } from "date-fns";

export default function CustomerDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [orders, setOrders] = useState<any[]>([]);
  const ws = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [threadId, setThreadId] = useState<string | null>(null);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (!storedUser) {
      router.push("/");
      return;
    }
    const parsedUser = JSON.parse(storedUser);
    if (parsedUser.role !== "customer") {
      router.push("/");
      return;
    }
    setUser(parsedUser);

    const fetchOrders = () => {
      fetch(`http://localhost:8006/chat/orders/${parsedUser.phone_number}`)
        .then((res) => res.json())
        .then((data) => setOrders(data))
        .catch((err) => console.error("Failed to fetch orders:", err));
    };

    // Fetch initial chat history and orders
    fetch(`http://localhost:8006/chat/history/${parsedUser.id}`)
      .then((res) => res.json())
      .then((data) => setMessages(data))
      .catch((err) => console.error("Failed to fetch history:", err));
      
    fetchOrders();

    // Initialize WebSocket
    ws.current = new WebSocket(`ws://localhost:8006/chat/ws/${parsedUser.id}`);
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "agent_message" && data.to_phone === parsedUser.phone_number) {
        setMessages((prev) => [
          ...prev,
          {
            id: Date.now().toString(),
            sender_id: "system", // Sangini AI
            message: data.message,
            timestamp: new Date().toISOString(),
            type: "text",
          },
        ]);
      } else if (data.type === "order_update") {
        fetchOrders();
      }
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    const newMessage = {
      id: Date.now().toString(),
      sender_id: user.id,
      message: inputMessage,
      timestamp: new Date().toISOString(),
      type: "text",
    };

    // Optimistic UI update
    setMessages((prev) => [...prev, newMessage]);
    setInputMessage("");

    // Send to LangGraph backend via REST
    try {
      if (threadId) {
        const res = await fetch("http://localhost:8006/resume", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            thread_id: threadId,
            customer_phone: user.phone_number,
            message: inputMessage,
          }),
        });
        const data = await res.json();
        // Update threadId just in case
        if (data.thread_id) setThreadId(data.thread_id);
      } else {
        const res = await fetch("http://localhost:8006/order", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            customer_phone: user.phone_number,
            message: inputMessage,
          }),
        });
        const data = await res.json();
        if (data.thread_id) setThreadId(data.thread_id);
      }
    } catch (error) {
      console.error("Failed to send message to backend:", error);
    }
  };

  if (!user) return null;

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar: Orders */}
      <div className="w-1/3 border-r bg-white flex flex-col">
        <div className="bg-green-600 p-4 text-white">
          <h2 className="text-xl font-bold">My Orders</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {orders
            .filter((order) => ["inventory_reserved", "allocated", "in_production", "ready_for_delivery", "completed"].includes(order.status))
            .map((order) => (
            <div key={order.id} className="rounded-lg border p-4 shadow-sm bg-gray-50">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-gray-800">Order #{order.id.slice(0,4)}</span>
                <span className="flex items-center text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">
                  <Clock size={12} className="mr-1" />
                  {order.status}
                </span>
              </div>
              {order.items.map((item: any, idx: number) => (
                <p key={idx} className="text-sm text-gray-600">{item.quantity}x {item.product_name}</p>
              ))}
              <div className="flex justify-between items-center mt-2">
                <p className="text-xs text-gray-400">Delivery: {order.deadline || "TBD"}</p>
                {order.created_at && (
                  <p className="text-xs text-gray-400">Ordered: {format(new Date(order.created_at), "MMM d, HH:mm")}</p>
                )}
              </div>
            </div>
          ))}
          {orders.filter((order) => ["inventory_reserved", "allocated", "in_production", "ready_for_delivery", "completed"].includes(order.status)).length === 0 && (
            <p className="text-sm text-gray-500 italic">No active orders found.</p>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="w-2/3 flex flex-col relative bg-[#E5DDD5]">
        {/* Chat Header */}
        <div className="bg-green-600 p-4 text-white flex items-center shadow-md z-10">
          <div className="w-10 h-10 rounded-full bg-green-200 flex items-center justify-center text-green-800 font-bold mr-3">
            S
          </div>
          <div>
            <h2 className="font-semibold">Sangini AI</h2>
            <p className="text-xs opacity-80">Online</p>
          </div>
        </div>

        {/* Messages list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg, index) => {
            const isMe = msg.sender_id === user.id;
            return (
              <div key={index} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[70%] rounded-lg p-3 shadow-sm ${
                    isMe ? "bg-[#DCF8C6] rounded-tr-none" : "bg-white rounded-tl-none"
                  }`}
                >
                  <p className="text-sm text-gray-800">{msg.message}</p>
                  <p className="text-[10px] text-gray-500 text-right mt-1">
                    {format(new Date(msg.timestamp), "HH:mm")}
                  </p>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input */}
        <div className="bg-gray-100 p-4">
          <form onSubmit={sendMessage} className="flex space-x-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Type a message..."
              className="flex-1 rounded-full border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-green-500 shadow-sm border"
            />
            <button
              type="submit"
              className="rounded-full bg-green-600 p-3 text-white hover:bg-green-700 focus:outline-none"
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
