import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Shield } from "lucide-react";
import { login } from "@/api/client";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-mocha-base px-4">
      <form onSubmit={handleSubmit} className="glass rounded-xl p-8 w-full max-w-sm space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center">
            <Shield className="w-5 h-5 text-indigo-400" />
          </div>
          <h1 className="text-xl font-semibold text-slate-100">ObservAI</h1>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Username</label>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-lg bg-mocha-mantle border border-mocha-crust px-3 py-2 text-slate-100 outline-none focus:border-indigo-400"
            autoFocus
          />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg bg-mocha-mantle border border-mocha-crust px-3 py-2 text-slate-100 outline-none focus:border-indigo-400"
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white py-2 font-medium"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
