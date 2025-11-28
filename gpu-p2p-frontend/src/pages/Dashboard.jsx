import PeersTable from "../components/PeersTable";
import JobsTable from "../components/JobsTable";
import CreateJobForm from "../components/CreateJobForm";

export default function Dashboard() {
  return (
    <div className="max-w-6xl mx-auto py-10 space-y-8">
      <h1 className="text-4xl font-bold text-center">P2P GPU Inference Dashboard</h1>
      <CreateJobForm />
      <PeersTable />
      <JobsTable />
    </div>
  );
}
