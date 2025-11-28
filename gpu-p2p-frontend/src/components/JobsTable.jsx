import { useEffect, useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

export default function JobsTable() {
  const [jobs, setJobs] = useState([]);

  useEffect(() => {
    axios.get(`${API}/jobs`).then((res) => setJobs(res.data));
  }, []);

  return (
    <div className="bg-white shadow rounded-lg p-6">
      <h2 className="text-2xl font-semibold mb-4">Jobs</h2>
      <table className="w-full border-collapse">
        <thead className="bg-gray-200">
          <tr>
            <th className="p-2 text-left">Job ID</th>
            <th className="p-2 text-left">Model</th>
            <th className="p-2 text-left">Status</th>
            <th className="p-2 text-left">Assigned Peer</th>
            <th className="p-2 text-left">Result</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id} className="border-b hover:bg-gray-50">
              <td className="p-2">{job.id.slice(0, 6)}...</td>
              <td className="p-2">{job.model_name}</td>
              <td className="p-2 font-semibold">{job.status}</td>
              <td className="p-2">{job.assigned_peer_id || "Pending"}</td>
              <td className="p-2">{job.result_url || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
