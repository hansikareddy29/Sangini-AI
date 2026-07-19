"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Send, Users, User as UserIcon } from "lucide-react";
import { format } from "date-fns";

export default function SHGDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [activeChat, setActiveChat] = useState<"group" | "private">("group");
  const [messages, setMessages] = useState<any[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const ws = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (!storedUser) {
      router.push("/");
      return;
    }
    const parsedUser = JSON.parse(storedUser);
    if (parsedUser.role !== "shg_member") {
      router.push("/");
      return;
    }
    setUser(parsedUser);

    // Initialize WebSocket
    ws.current = new WebSocket(`ws://localhost:8006/chat/ws/${parsedUser.id}`);
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // For now, we'll just push all incoming messages to the current active view if they match
      if (data.type === "agent_message" && data.to_phone === parsedUser.phone_number) {
         if (activeChat === "private") {
            setMessages((prev) => [
            ...prev,
            {
                id: Date.now().toString(),
                sender_id: "system", 
                message: data.message,
                timestamp: new Date().toISOString(),
                type: "text",
            },
            ]);
         }
      } else if (data.type === "shg_message") {
         if (activeChat === "private") {
            setMessages((prev) => [
            ...prev,
            {
                id: Date.now().toString(),
                sender_id: "system", 
                message: data.message,
                timestamp: new Date().toISOString(),
                type: "text",
            },
            ]);
         }
      }
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [router, activeChat]);

  // Handle switching chats
  useEffect(() => {
    if (!user) return;
    
    // In a real app we'd fetch history based on `activeChat`
    // For demo purposes we will reset and maybe fetch group history
    setMessages([]);
    
    if (activeChat === "private") {
        fetch(`http://localhost:8006/chat/history/${user.id}`)
        .then((res) => res.json())
        .then((data) => setMessages(data))
        .catch((err) => console.error("Failed to fetch history:", err));
    } else {
        // Group Chat History
        // We need the group ID, but we can hardcode for the hackathon demo if we assume 1 group
        setMessages([
            {
                id: "1",
                sender_id: "system",
                message: "New Order Received: 50 Mango Pickles\nDelivery: Friday\nReply with 'I can make X'",
                timestamp: new Date().toISOString(),
                type: "text",
            }
        ]);
    }
  }, [activeChat, user]);


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

    setMessages((prev) => [...prev, newMessage]);
    setInputMessage("");

    // Here we'd send to backend depending on if it's group or private
  };

  if (!user) return null;

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar: Chat List */}
      <div className="w-1/3 border-r bg-white flex flex-col">
        <div className="bg-green-600 p-4 text-white flex items-center justify-between">
          <div className="flex items-center">
            <div className="w-10 h-10 rounded-full bg-white text-green-600 flex items-center justify-center font-bold mr-3">
              {user.name.charAt(0)}
            </div>
            <h2 className="text-xl font-bold">{user.name}</h2>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {/* Group Chat Button */}
          <div 
            onClick={() => setActiveChat("group")}
            className={`flex items-center p-4 cursor-pointer border-b ${activeChat === "group" ? "bg-gray-100" : "hover:bg-gray-50"}`}
          >
            <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 mr-4">
              <Users size={24} />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-800">Women's SHG</h3>
              <p className="text-sm text-gray-500 truncate">Group updates and allocations...</p>
            </div>
          </div>

          {/* Private AI Chat Button */}
          <div 
            onClick={() => setActiveChat("private")}
            className={`flex items-center p-4 cursor-pointer border-b ${activeChat === "private" ? "bg-gray-100" : "hover:bg-gray-50"}`}
          >
            <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 mr-4">
              <UserIcon size={24} />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-800">Sangini AI (Private)</h3>
              <p className="text-sm text-gray-500 truncate">Your tasks and assignments...</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="w-2/3 flex flex-col relative bg-[#E5DDD5]">
        {/* Chat Header */}
        <div className="bg-green-600 p-4 text-white flex items-center shadow-md z-10">
          <div>
            <h2 className="font-semibold">
              {activeChat === "group" ? "Women's SHG" : "Sangini AI (Private)"}
            </h2>
            <p className="text-xs opacity-80">
              {activeChat === "group" ? "You, Anita, Lakshmi, Rekha, Sangini AI" : "Online"}
            </p>
          </div>
        </div>

        {/* Messages list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((msg, index) => {
            const isMe = msg.sender_id === user.id;
            const isSystem = msg.sender_id === "system";
            
            return (
              <div key={index} className={`flex ${isMe ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[70%] rounded-lg p-3 shadow-sm ${
                    isMe 
                      ? "bg-[#DCF8C6] rounded-tr-none" 
                      : isSystem 
                        ? "bg-purple-100 border border-purple-200 rounded-tl-none" 
                        : "bg-white rounded-tl-none"
                  }`}
                >
                  {!isMe && activeChat === "group" && !isSystem && (
                      <p className="text-xs font-bold text-blue-600 mb-1">{msg.sender_id}</p>
                  )}
                  {!isMe && isSystem && (
                      <p className="text-xs font-bold text-purple-600 mb-1">Sangini AI</p>
                  )}
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{msg.message}</p>
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
