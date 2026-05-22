"use client";

import { Gauge, Lock, Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { login } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export default function LoginPage() {
  const router = useRouter();
  const { setAccessToken, setOrganizationId } = useAppStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await login(email, password);
      setAccessToken(data.access_token);
      setOrganizationId(data.user.organization_id);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f6f8fb]">
      <div className="w-full max-w-sm rounded-lg border border-line bg-white p-8 shadow-soft">
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent text-white">
            <Gauge size={24} />
          </div>
          <h1 className="text-xl font-semibold">WexaAI Analytics</h1>
          <p className="text-sm text-muted">Sign in to your workspace</p>
        </div>

        {error && (
          <div className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="focus-ring h-10 w-full rounded border border-line bg-slate-50 pl-9 pr-3 text-sm"
                placeholder="you@example.com"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Password</label>
            <div className="relative">
              <Lock className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="focus-ring h-10 w-full rounded border border-line bg-slate-50 pl-9 pr-3 text-sm"
                placeholder="••••••••"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="focus-ring w-full rounded bg-accent py-2.5 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-muted">
          No account?{" "}
          <a href="/signup" className="font-medium text-accent hover:underline">
            Sign up
          </a>
        </p>
      </div>
    </div>
  );
}
