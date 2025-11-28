import { useEffect, useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

export default function PeersTable() {
  const [peers, setPeers] = useState([]);

  useEffect(() => {
    axios.get(`${API}/peers`).then((res) => setPeers(res.data));
  }, []);

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-2xl font-semibold mb-4">Active Peers</h2>
      <table className="w-full border-collapse">
        <thead className="bg-gray-200">
          <tr>
            <th className="p-2 text-left">Name</th>
            <th className="p-2 text-left">GPU</th>
            <th className="p-2 text-left">Free VRAM</th>
            <th className="p-2 text-left">Models</th>
            <th className="p-2 text-left">Status</th>
          </tr>
        </thead>
        <tbody>
          {peers.map((peer) => (
            <tr key={peer.id} className="border-b hover:bg-gray-50">
              <td className="p-2 font-medium">{peer.name}</td>
              <td className="p-2">{peer.has_gpu ? "Yes" : "No"}</td>
              <td className="p-2">{peer.gpu_memory_free_mb || "—"}</td>
              <td className="p-2">{peer.models.map((m) => m.name).join(", ")}</td>
              <td className={`p-2 font-bold ${peer.is_online ? "text-green-600" : "text-red-600"}`}>
                {peer.is_online ? "Online" : "Offline"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
