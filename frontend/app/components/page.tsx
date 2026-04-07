"use client";
import type { ChangeEvent } from "react";
import { useEffect, useRef, useState } from "react";
import Layout from "./Layout";
import EnrichmentBadge from "./EnrichmentBadge";
import { apiFetch } from "../lib/api";

interface Component { id: string; name_internal: string; name_normalized: string | null; enrichment_status: string; category_id: string | null; }

export default function ComponentsPage() {
  const [components, setComponents] = useState<Component[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = () => apiFetch<Component[]>("/components").then(setComponents);
  useEffect(() => { load(); }, []);

  const handleEnrich = async (id: string) => {
    await apiFetch(`/components/${id}/enrich`, { method: "POST" });
    alert("Задача на обогащение поставлена в очередь");
  };

  const handleImport = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const result = await fetch(`${apiUrl}/components/import`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    }).then(r => r.json());
    alert(`Импортировано: ${result.imported}, пропущено: ${result.skipped}`);
    load();
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Компоненты</h1>
        <div className="flex gap-2">
          <button type="button" onClick={() => fileRef.current?.click()} className="text-sm bg-white border border-gray-300 rounded px-3 py-1.5 hover:bg-gray-50">
            Импорт CSV
          </button>
          <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleImport} />
        </div>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Название (внутреннее)</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Нормализованное</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Статус</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {components.map(c => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-900">{c.name_internal}</td>
                <td className="px-4 py-3 text-gray-500">{c.name_normalized ?? "—"}</td>
                <td className="px-4 py-3"><EnrichmentBadge status={c.enrichment_status} /></td>
                <td className="px-4 py-3 text-right">
                  {c.enrichment_status === "pending" && (
                    <button type="button" onClick={() => handleEnrich(c.id)} className="text-xs text-blue-600 hover:text-blue-800">
                      Обогатить
                    </button>
                  )}
                  {c.enrichment_status === "in_review" && (
                    <a href="/components/review" className="text-xs text-yellow-600 hover:text-yellow-800">
                      Проверить →
                    </a>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
