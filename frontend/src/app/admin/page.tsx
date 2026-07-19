"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Users, Package, Activity, LogOut, X, ChevronRight, CheckCircle2, Clock } from "lucide-react";

interface AdminStats {
  active_orders: number;
  shg_members_online: number;
  pending_allocations: number;
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
    pending_allocations: 0
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

    // Fetch initial stats
    fetch("http://localhost:8006/admin/stats")
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error("Failed to fetch admin stats", err));

    // Poll stats every 5 seconds
    const interval = setInterval(() => {
      fetch("http://localhost:8006/admin/stats")
        .then(res => res.json())
        .then(data => setStats(data))
        .catch(err => console.error("Failed to fetch admin stats", err));
    }, 5000);

    // Connect WebSocket
    const ws = new WebSocket(`ws://localhost:8006/chat/ws/${parsedUser.id}`);
    
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
    fetch("http://localhost:8006/admin/orders")
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

        <div className="grid gap-6 md:grid-cols-3">
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
        </div>

        <div className="mt-8 rounded-xl border bg-white shadow-sm">
          <div className="border-b p-6">
            <h3 className="text-lg font-semibold text-gray-900">Live AI Activity Log</h3>
          </div>
          <div className="p-6 h-96 overflow-y-auto space-y-4 font-mono text-sm">
            {logs.length === 0 ? (
              <div className="text-gray-400 italic">No recent activity. Place an order to see AI logs.</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="flex items-center space-x-3">
                  <span className="text-gray-400">{log.timestamp}</span>
                  <span className={
                    log.agent === 'OrderAgent' ? 'text-blue-600' :
                    log.agent === 'InventoryAgent' ? 'text-purple-600' :
                    log.agent === 'AllocationAgent' ? 'text-green-600' :
                    'text-gray-600'
                  }>
                    {log.agent}: {log.message}
                  </span>
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>

      {/* Active Orders Modal */}
      {isOrdersModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
            <div className="px-6 py-4 border-b flex justify-between items-center bg-gray-50/80">
              <h2 className="text-xl font-bold text-gray-900 flex items-center space-x-2">
                <Package className="text-green-600" size={24} />
                <span>Active Orders Details</span>
              </h2>
              <button onClick={() => setIsOrdersModalOpen(false)} className="p-2 text-gray-400 hover:bg-gray-200 hover:text-gray-700 rounded-full transition-colors">
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1 bg-gray-50/30">
              {isLoadingOrders ? (
                <div className="flex justify-center items-center h-48">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
                </div>
              ) : activeOrders.length === 0 ? (
                <div className="text-center text-gray-500 py-12">
                  <Package size={48} className="mx-auto text-gray-300 mb-4" />
                  <p className="text-lg">No active orders found.</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {activeOrders.map(order => (
                    <div key={order.id} className="bg-white border rounded-xl shadow-sm overflow-hidden transition-shadow hover:shadow-md">
                      <div className="px-6 py-4 border-b bg-gray-50 flex justify-between items-center">
                        <div className="flex items-center space-x-4">
                          <span className="font-mono text-sm text-gray-500">#{order.id.substring(0,8)}</span>
                          <span className="text-sm font-medium text-gray-900">{order.customer_phone}</span>
                        </div>
                        {getStatusBadge(order.status)}
                      </div>
                      
                      <div className="px-6 py-4 divide-y">
                        {order.items.map((item, idx) => (
                          <div key={idx} className="py-4 first:pt-0 last:pb-0">
                            <div className="flex justify-between items-center mb-3">
                              <h4 className="font-semibold text-gray-800">{item.quantity}x {item.product_name}</h4>
                            </div>
                            
                            {item.allocations.length > 0 ? (
                              <div className="bg-green-50/50 rounded-lg p-3 border border-green-100">
                                <h5 className="text-xs font-bold text-green-800 uppercase tracking-wider mb-2">SHG Allocations</h5>
                                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                                  {item.allocations.map((alloc, aidx) => (
                                    <div key={aidx} className="flex items-center space-x-2 bg-white rounded-md p-2 shadow-sm border border-green-50">
                                      <div className="w-8 h-8 rounded-full bg-green-100 text-green-700 flex items-center justify-center font-bold text-xs">
                                        {alloc.member_name.charAt(0)}
                                      </div>
                                      <div>
                                        <div className="text-sm font-medium text-gray-900">{alloc.member_name}</div>
                                        <div className="text-xs text-gray-500">{alloc.allocated_quantity} units</div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ) : (
                              <div className="text-sm text-gray-400 italic">No specific SHG member allocations for this item yet.</div>
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
        </div>
      )}
    </div>
  );
}

