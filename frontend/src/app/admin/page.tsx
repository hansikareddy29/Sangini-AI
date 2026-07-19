"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Users, Package, Activity, LogOut, X, ChevronRight, CheckCircle2, Clock } from "lucide-react";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8006";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8006";


interface AdminStats {
  active_orders: number;
  shg_members_online: number;
  pending_allocations: number;
  detailed_inventory?: {name: string; quantity: number}[];
}

interface AdminLog {
  timestamp: string;
  agent: string;
  message: string;
}

interface AllocationDetail {
  member_name: string;
  allocated_quantity: number;
  status: string;
}

interface OrderItemDetail {
  product_name: string;
  quantity: number;
  reserved_from_inventory: number;
  allocations: AllocationDetail[];
}

interface OrderDetail {
  id: string;
  customer_phone: string;
  status: string;
  created_at: string;
  items: OrderItemDetail[];
}

export default function AdminDashboard() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [stats, setStats] = useState<AdminStats>({
    active_orders: 0,
    shg_members_online: 0,
    pending_allocations: 0,
    detailed_inventory: []
  });
  const [logs, setLogs] = useState<AdminLog[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Modal State
  const [isOrdersModalOpen, setIsOrdersModalOpen] = useState(false);
  const [activeOrders, setActiveOrders] = useState<OrderDetail[]>([]);
  const [isLoadingOrders, setIsLoadingOrders] = useState(false);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    if (!storedUser) {
      router.push("/");
      return;
    }
    const parsedUser = JSON.parse(storedUser);
    if (parsedUser.role !== "admin") {
      router.push("/");
      return;
    }
    setUser(parsedUser);

    // Fetch initial stats & orders
    fetch(`${BACKEND_URL}/admin/stats`)
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error("Failed to fetch admin stats", err));
      
    fetch(`${BACKEND_URL}/admin/orders`)
      .then(res => res.json())
      .then(data => setActiveOrders(data))
      .catch(err => console.error("Failed to fetch active orders", err));

    fetch(`${BACKEND_URL}/admin/logs`)
      .then(res => res.json())
      .then(data => setLogs(data))
      .catch(err => console.error("Failed to fetch admin logs", err));

    // Poll stats every 5 seconds
    const interval = setInterval(() => {
      fetch(`${BACKEND_URL}/admin/stats`)
        .then(res => res.json())
        .then(data => setStats(data))
        .catch(err => console.error("Failed to fetch admin stats", err));
        
      fetch(`${BACKEND_URL}/admin/orders`)
        .then(res => res.json())
        .then(data => setActiveOrders(data))
        .catch(err => console.error("Failed to fetch active orders", err));
    }, 5000);

    // Connect WebSocket
    const ws = new WebSocket(`${WS_URL}/chat/ws/${parsedUser.id}`);
    
    ws.onopen = () => {
      console.log("Admin WebSocket connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "admin_log") {
          setLogs(prev => [...prev, {
            timestamp: data.timestamp,
            agent: data.agent,
            message: data.message
          }]);
        }
      } catch (e) {
        console.error("Error parsing admin ws message:", e);
      }
    };

    ws.onclose = () => {
      console.log("Admin WebSocket disconnected");
    };

    return () => {
      clearInterval(interval);
      ws.close();
    };
  }, [router]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const handleOpenOrdersModal = () => {
    setIsOrdersModalOpen(true);
    setIsLoadingOrders(true);
    fetch(`${BACKEND_URL}/admin/orders`)
      .then(res => res.json())
      .then(data => {
        setActiveOrders(data);
        setIsLoadingOrders(false);
      })
      .catch(err => {
        console.error("Failed to fetch active orders", err);
        setIsLoadingOrders(false);
      });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'allocated':
        return <span className="inline-flex items-center space-x-1 rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-700"><CheckCircle2 size={12} /><span>Allocated</span></span>;
      case 'partially_allocated':
        return <span className="inline-flex items-center space-x-1 rounded-full bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-700"><Clock size={12} /><span>Partial</span></span>;
      default:
        return <span className="inline-flex items-center space-x-1 rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-700"><Clock size={12} /><span>{status.replace('_', ' ')}</span></span>;
    }
  };

  if (!user) return null;

  return (
    <div className="flex min-h-screen bg-gray-50 relative">
      {/* Sidebar */}
      <div className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-bold tracking-tight text-green-400">Sangini Admin</h1>
        </div>
        <nav className="flex-1 space-y-2 p-4">
          <div className="flex items-center space-x-3 rounded-lg bg-gray-800 p-3 text-white">
            <Activity size={20} />
            <span className="font-medium">Live Activity</span>
          </div>
        </nav>
        <div className="p-4 border-t border-gray-800">
          <button 
            onClick={() => {
              localStorage.removeItem("user");
              router.push("/");
            }}
            className="flex w-full items-center space-x-3 rounded-lg p-3 text-gray-400 hover:bg-red-500 hover:text-white transition-colors"
          >
            <LogOut size={20} />
            <span className="font-medium">Sign Out</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-8">
        <div className="mb-8 flex items-center justify-between">
          <h2 className="text-3xl font-bold text-gray-900">Dashboard Overview</h2>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span>System Live</span>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-4">
          <div 
            onClick={handleOpenOrdersModal}
            className="rounded-xl border bg-white p-6 shadow-sm cursor-pointer hover:shadow-md hover:scale-105 hover:border-green-400 transition-all group"
          >
            <div className="flex justify-between items-start">
              <h3 className="text-sm font-medium text-gray-500 group-hover:text-green-600 transition-colors">Active Orders</h3>
              <ChevronRight size={16} className="text-gray-300 group-hover:text-green-500 transition-colors" />
            </div>
            <p className="mt-2 text-3xl font-bold text-gray-900">{stats.active_orders}</p>
          </div>
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-500">SHG Members Online</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">{stats.shg_members_online}</p>
          </div>
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-500">Pending Allocations</h3>
            <p className="mt-2 text-3xl font-bold text-gray-900">{stats.pending_allocations}</p>
          </div>
          <div className="rounded-xl border bg-white p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-500 mb-4">Detailed Inventory Items</h3>
            <div className="space-y-3">
              {stats.detailed_inventory && stats.detailed_inventory.length > 0 ? (
                stats.detailed_inventory.map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center bg-gray-50 p-2 rounded-md">
                    <span className="font-medium text-gray-700">{item.name}</span>
                    <span className="font-bold text-green-600">{item.quantity}</span>
                  </div>
                ))
              ) : (
                <div className="text-sm text-gray-400">No inventory available.</div>
              )}
            </div>
          </div>
        </div>

        <div className="mt-8 grid gap-8 md:grid-cols-2">
          {/* Active Orders List */}
          <div className="rounded-xl border bg-white shadow-sm flex flex-col h-[500px]">
            <div className="border-b p-6 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                <Package className="text-green-600" size={20} />
                <span>Live Orders & Allocations</span>
              </h3>
            </div>
            <div className="p-6 flex-1 overflow-y-auto bg-gray-50/50">
              {activeOrders.length === 0 ? (
                <div className="text-center text-gray-500 py-12">
                  <Package size={48} className="mx-auto text-gray-300 mb-4" />
                  <p className="text-sm">No active orders right now.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {activeOrders.map(order => (
                    <div key={order.id} className="bg-white border rounded-xl shadow-sm overflow-hidden">
                      <div className="px-4 py-3 border-b bg-gray-50 flex justify-between items-center">
                        <div className="flex items-center space-x-3">
                          <span className="font-mono text-xs text-gray-500">#{order.id.substring(0,8)}</span>
                          <span className="text-xs font-medium text-gray-900">{order.customer_phone}</span>
                        </div>
                        {getStatusBadge(order.status)}
                      </div>
                      
                      <div className="px-4 py-3 divide-y">
                        {order.items.map((item, idx) => (
                          <div key={idx} className="py-3 first:pt-0 last:pb-0">
                            <div className="flex justify-between items-center mb-2">
                              <h4 className="font-medium text-sm text-gray-800">{item.quantity}x {item.product_name}</h4>
                            </div>
                            
                            {item.reserved_from_inventory >= item.quantity ? (
                              <div className="text-xs text-emerald-600 italic bg-emerald-50 px-2 py-1 rounded border border-emerald-100 inline-block font-medium flex items-center space-x-1">
                                <CheckCircle2 size={12} />
                                <span>Fulfilled directly from Community Inventory</span>
                              </div>
                            ) : item.allocations.length > 0 ? (
                              <div className="bg-green-50/50 rounded-lg p-2 border border-green-100">
                                <h5 className="text-[10px] font-bold text-green-800 uppercase tracking-wider mb-1.5 flex justify-between">
                                  <span>Allocated To SHG Members</span>
                                  {item.reserved_from_inventory > 0 && (
                                    <span className="text-emerald-600 lowercase font-normal italic">({item.reserved_from_inventory} taken from inventory)</span>
                                  )}
                                </h5>
                                <div className="grid grid-cols-2 gap-2">
                                  {item.allocations.map((alloc, aidx) => (
                                    <div key={aidx} className="flex items-center space-x-2 bg-white rounded-md p-1.5 shadow-sm border border-green-50">
                                      <div className="w-6 h-6 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-bold text-[10px]">
                                        {alloc.member_name.charAt(0)}
                                      </div>
                                      <div>
                                        <div className="text-xs font-medium text-gray-900 truncate max-w-[80px]">{alloc.member_name}</div>
                                        <div className="text-[10px] text-gray-500">{alloc.allocated_quantity} units</div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ) : (
                              <div className="flex items-center space-x-2">
                                {item.reserved_from_inventory > 0 && (
                                  <div className="text-[10px] text-emerald-600 italic bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100">
                                    {item.reserved_from_inventory} from inventory
                                  </div>
                                )}
                                <div className="text-xs text-orange-500 italic bg-orange-50 px-2 py-1 rounded border border-orange-100 inline-block">Pending allocation</div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* AI Activity Log */}
          <div className="rounded-xl border bg-white shadow-sm flex flex-col h-[500px]">
            <div className="border-b p-6">
              <h3 className="text-lg font-semibold text-gray-900">Live AI Activity Log</h3>
            </div>
            <div className="p-6 flex-1 overflow-y-auto space-y-4 font-mono text-sm">
              {logs.length === 0 ? (
                <div className="text-gray-400 italic">No recent activity. Place an order to see AI logs.</div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="flex items-start space-x-3">
                    <span className="text-gray-400 shrink-0 mt-0.5">{log.timestamp}</span>
                    <span className={
                      log.agent === 'OrderAgent' ? 'text-blue-600' :
                      log.agent === 'InventoryAgent' ? 'text-purple-600' :
                      log.agent === 'AllocationAgent' ? 'text-green-600' :
                      'text-gray-600'
                    }>
                      <span className="font-semibold">{log.agent}:</span> {log.message}
                    </span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

