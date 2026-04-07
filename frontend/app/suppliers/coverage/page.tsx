"use client";
import { useEffect, useState } from "react";
import Layout from "../../components/Layout";
import CoverageBar from "../../components/CoverageBar";
import { apiFetch } from "../../lib/api";

interface CoverageItem { category_id: string; category_name: string; supplier_count: number; status: string; }

export default function CoveragePage() {
  const [items, setItems] = useState<CoverageItem[]>([]);
  useEffect(() => { apiFetch<CoverageItem[]>("/suppliers/coverage").then(setItems).catch(console.error); }, []);

  const red = items.filter(i => i.status === "red");
  const yellow = items.filter(i => i.status === "yellow");
  const green = items.filter(i => i.status === "green");

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Покрытие поставщиков</h1>
      {[
        { label: "Критично — нет поставщиков", items: red, color: "text-red-600" },
        { label: "Мало поставщиков (2–3)", items: yellow, color: "text-yellow-600" },
        { label: "Хорошее покрытие (4+)", items: green, color: "text-green-600" },
      ].map(group => group.items.length > 0 && (
        <div key={group.label} className="mb-6">
          <h2 className={`text-sm font-semibold uppercase tracking-wide mb-3 ${group.color}`}>{group.label}</h2>
          <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
            {group.items.map(item => (
              <div key={item.category_id} className="flex items-center gap-4 px-4 py-3">
                <span className="text-sm text-gray-900 flex-1">{item.category_name}</span>
                <div className="w-40">
                  <CoverageBar count={item.supplier_count} status={item.status} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </Layout>
  );
}
