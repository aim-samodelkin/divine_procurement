"use client";
import { useEffect, useState } from "react";
import Layout from "../Layout";
import { apiFetch } from "../../lib/api";

interface Component { id: string; name_internal: string; name_normalized: string | null; search_queries: string[]; category_id: string | null; enrichment_status: string; }
interface Category { id: string; name: string; }

export default function EnrichmentReviewPage() {
  const [components, setComponents] = useState<Component[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  const load = async () => {
    const all = await apiFetch<Component[]>("/components");
    setComponents(all.filter(c => c.enrichment_status === "in_review"));
    const cats = await apiFetch<Category[]>("/categories");
    setCategories(cats);
  };

  useEffect(() => { load(); }, []);

  const approve = async (comp: Component, categoryId: string) => {
    await apiFetch(`/components/${comp.id}`, {
      method: "PATCH",
      body: JSON.stringify({ category_id: categoryId, enrichment_status: "enriched" }),
    });
    load();
  };

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Ревью обогащения</h1>
      {components.length === 0 && <p className="text-gray-500">Нет компонентов на ревью.</p>}
      <div className="space-y-4">
        {components.map(c => (
          <div key={c.id} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="text-sm text-gray-500 mb-1">Исходное: {c.name_internal}</div>
            <div className="font-medium text-gray-900 mb-2">{c.name_normalized}</div>
            {c.search_queries.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-3">
                {c.search_queries.map((q, i) => (
                  <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">{q}</span>
                ))}
              </div>
            )}
            <div className="flex items-center gap-2">
              <select
                defaultValue={c.category_id ?? ""}
                onChange={e => approve(c, e.target.value)}
                className="text-sm border border-gray-300 rounded px-2 py-1"
              >
                <option value="" disabled>Выбрать категорию...</option>
                {categories.map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
              </select>
              <span className="text-xs text-gray-400">Выбери категорию для подтверждения</span>
            </div>
          </div>
        ))}
      </div>
    </Layout>
  );
}
