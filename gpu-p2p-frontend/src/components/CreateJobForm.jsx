import { useState } from "react";
import axios from "axios";

const API = "http://localhost:8000";

export default function CreateJobForm() {
  const [requesterId, setRequesterId] = useState("");
  const [payloadUrl, setPayloadUrl] = useState("");

  function submitJob() {
    axios.post(`${API}/jobs`, {
      requester_peer_id: requesterId,
      model_name: "resnet50",
      payload_url: payloadUrl,
    }).then(() => alert("Job Created"));
  }

  return (
    <div className="bg-white shadow rounded-lg p-6 space-y-4">
      <h2 className="text-2xl font-semibold">Create New Job</h2>

      <input
        placeholder="Requester Peer ID"
        className="border p-2 rounded w-full"
        value={requesterId}
        onChange={(e) => setRequesterId(e.target.value)}
      />

      <input
        placeholder="Image URL"
        className="border p-2 rounded w-full"
        value={payloadUrl}
        onChange={(e) => setPayloadUrl(e.target.value)}
      />

      <button onClick={submitJob} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
        Submit Job
      </button>
    </div>
  );
}
