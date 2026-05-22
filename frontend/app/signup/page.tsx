"use client";

import { Building2, Gauge, Lock, Mail, User } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { signup } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export default function SignupPage() {
  const router = useRouter();
  const { setAccessToken, setOrganizationId } = useAppStore();
  const [form, setForm] = useState({
    organization_name: "",
    organization_slug: "",
    full_name: "",
    email: "",
    password: ""
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function field(key: keyof typeof form) {
    return {
      value: form[key],
      onChange: (e: React.ChangeEvent<HTMLInputElement>) => setForm((f) => ({ ...f, [key]: e.target.value }))
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await signup(form);
      setAccessToken(data.access_token);
      setOrganizationId(data.user.organization_id);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f6f8fb] px-4">
      <div className="w-full max-w-sm rounded-lg border border-line bg-white p-8 shadow-soft">
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent text-white">
            <Gauge size={24} />
          </div>
          <h1 className="text-xl font-semibold">Create workspace</h1>
          <p className="text-sm text-muted">Set up your WexaAI organisation</p>
        </div>

        {error && (
          <div className="mb-4 rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          {[
            { key: "organization_name" as const, label: "Organisation name", icon: Building2, placeholder: "Acme Corp" },
            { key: "organization_slug" as const, label: "Slug (URL)", icon: Building2, placeholder: "acme-corp" },
            { key: "full_name" as const, label: "Your name", icon: User, placeholder: "Jane Doe" },
            { key: "email" as const, label: "Email", icon: Mail, placeholder: "jane@acme.com", type: "email" },
            { key: "password" as const, label: "Password", icon: Lock, placeholder: "••••••••", type: "password" }
          ].map(({ key, label, icon: Icon, placeholder, type = "text" }) => (
            <div key={key}>
              <label className="mb-1 block text-sm font-medium">{label}</label>
              <div className="relative">
                <Icon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
                <input
                  type={type}
                  required
                  placeholder={placeholder}
                  className="focus-ring h-10 w-full rounded border border-line bg-slate-50 pl-9 pr-3 text-sm"
                  {...field(key)}
                />
              </div>
            </div>
          ))}

          <button
            type="submit"
            disabled={loading}
            className="focus-ring mt-2 w-full rounded bg-accent py-2.5 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {loading ? "Creating…" : "Create workspace"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-muted">
          Already have an account?{" "}
          <a href="/login" className="font-medium text-accent hover:underline">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
