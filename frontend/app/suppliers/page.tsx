"use client";
import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../lib/api";

interface Supplier { id: string; name: string; type: string; email: string | null; website: string | null; }

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [form, setForm] = useState({ name: "", type: "company", email: "", website: "" });
  const [adding, setAdding] = useState(false);

  const load = () => apiFetch<Supplier[]>("/suppliers").then(setSuppliers);
  useEffect(() => { load(); }, []);

  const submit = async () => {
    await apiFetch("/suppliers", { method: "POST", body: JSON.stringify(form) });
    setAdding(false);
    load();
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Поставщики</h1>
        <button type="button" onClick={() => setAdding(true)} className="text-sm bg-blue-600 text-white rounded px-3 py-1.5 hover:bg-blue-700">
          Добавить
        </button>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Название</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Тип</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Сайт</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {suppliers.map(s => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{s.name}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${s.type === "company" ? "bg-blue-100 text-blue-700" : "bg-purple-100 text-purple-700"}`}>
                    {s.type === "company" ? "Компания" : "Площадка"}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{s.email ?? "—"}</td>
                <td className="px-4 py-3 text-gray-500">
                  {s.website ? <a href={s.website} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{s.website}</a> : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {adding && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96 space-y-3 shadow-xl">
            <h3 className="font-semibold">Новый поставщик</h3>
            {[
              { label: "Название", key: "name", type: "text" },
              { label: "Email", key: "email", type: "email" },
              { label: "Сайт", key: "website", type: "url" },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-sm text-gray-600 mb-1">{f.label}</label>
                <input
                  type={f.type}
                  value={(form as Record<string, string>)[f.key]}
                  onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              </div>
            ))}
            <div>
              <label className="block text-sm text-gray-600 mb-1">Тип</label>
              <select value={form.type} onChange={e => setForm(prev => ({ ...prev, type: e.target.value }))}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm">
                <option value="company">Компания</option>
                <option value="marketplace">Площадка</option>
              </select>
            </div>
            <div className="flex gap-2 justify-end">
              <button type="button" onClick={() => setAdding(false)} className="text-sm text-gray-500 px-3 py-1.5 hover:bg-gray-100 rounded">Отмена</button>
              <button type="button" onClick={submit} className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700">Создать</button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
