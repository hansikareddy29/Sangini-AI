"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { User, Users, Shield, ArrowRight } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch users from backend
    fetch("http://localhost:8006/chat/users")
      .then((res) => res.json())
      .then((data) => {
        setUsers(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch users", err);
        setLoading(false);
      });
  }, []);

  const handleLogin = (user: any) => {
    // Save user to local storage for simple mock auth
    localStorage.setItem("user", JSON.stringify(user));
    
    // Redirect based on role
    if (user.role === "customer") {
      router.push("/customer");
    } else if (user.role === "shg_member") {
      router.push("/shg");
    } else if (user.role === "admin") {
      router.push("/admin");
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-50">
        <div className="animate-pulse text-lg text-gray-500">Connecting to Sangini AI...</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-6">
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-6xl">
          Sangini <span className="text-green-600">AI</span>
        </h1>
        <p className="mt-4 text-lg text-gray-600">
          Select a role to test the multi-agent workflow
        </p>
      </div>

      <div className="grid w-full max-w-4xl gap-6 md:grid-cols-3">
        {/* Customer Login Options */}
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-blue-100 text-blue-600">
            <User size={24} />
          </div>
          <h2 className="mb-2 text-xl font-semibold">Customers</h2>
          <p className="mb-6 text-sm text-gray-500">
            Place orders, request quotations, and track delivery via chat.
          </p>
          <div className="space-y-2">
            {users.filter(u => u.role === "customer").map(user => (
              <button
                key={user.id}
                onClick={() => handleLogin(user)}
                className="flex w-full items-center justify-between rounded-lg border p-3 text-left hover:bg-gray-50"
              >
                <span className="font-medium">{user.name}</span>
                <ArrowRight size={16} className="text-gray-400" />
              </button>
            ))}
          </div>
        </div>

        {/* SHG Member Login Options */}
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 text-green-600">
            <Users size={24} />
          </div>
          <h2 className="mb-2 text-xl font-semibold">SHG Members</h2>
          <p className="mb-6 text-sm text-gray-500">
            Coordinate with your group and receive production assignments.
          </p>
          <div className="space-y-2">
            {users.filter(u => u.role === "shg_member").map(user => (
              <button
                key={user.id}
                onClick={() => handleLogin(user)}
                className="flex w-full items-center justify-between rounded-lg border p-3 text-left hover:bg-gray-50"
              >
                <span className="font-medium">{user.name}</span>
                <ArrowRight size={16} className="text-gray-400" />
              </button>
            ))}
          </div>
        </div>

        {/* Admin Login Options */}
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-purple-100 text-purple-600">
            <Shield size={24} />
          </div>
          <h2 className="mb-2 text-xl font-semibold">Admins</h2>
          <p className="mb-6 text-sm text-gray-500">
            Monitor active orders and observe AI decision-making.
          </p>
          <div className="space-y-2">
            {users.filter(u => u.role === "admin").map(user => (
              <button
                key={user.id}
                onClick={() => handleLogin(user)}
                className="flex w-full items-center justify-between rounded-lg border p-3 text-left hover:bg-gray-50"
              >
                <span className="font-medium">{user.name}</span>
                <ArrowRight size={16} className="text-gray-400" />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
