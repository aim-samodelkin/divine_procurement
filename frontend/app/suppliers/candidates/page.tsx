"use client";
import { useCallback, useEffect, useState } from "react";
import Layout from "../../components/Layout";
import { ApiError, apiFetch } from "../../lib/api";

interface Candidate {
  id: string;
  name: string;
  source: string;
  completeness: string;
  email: string | null;
  website: string | null;
  status: string;
}

export default function SupplierCandidatesPage() {
  const [rows, setRows] = useState<Candidate[]>([]);
  const [componentId, setComponentId] = useState("");
  const [discovering, setDiscovering] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(() => {
    setErr(null);
    return apiFetch<Candidate[]>("/supplier-candidates?status=pending").then(setRows).catch(e => {
      setErr(e instanceof ApiError ? e.message : String(e));
    });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runDiscover = async () => {
    const id = componentId.trim();
    if (!id) {
      setErr("Укажите UUID компонента");
      return;
    }
    setDiscovering(true);
    setErr(null);
    try {
      await apiFetch(`/components/${id}/discover-suppliers`, { method: "POST" });
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setDiscovering(false);
    }
  };

  const approve = async (id: string) => {
    await apiFetch(`/supplier-candidates/${id}/approve`, { method: "POST" });
    await load();
  };

  const reject = async (id: string) => {
    await apiFetch(`/supplier-candidates/${id}/reject`, { method: "POST" });
    await load();
  };

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Кандидаты поставщиков</h1>

      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6 space-y-3">
        <p className="text-sm text-gray-600">Запуск поиска по компоненту (нужны обогащённые search_queries или имя):</p>
        <div className="flex flex-wrap gap-2 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs text-gray-500 mb-1">UUID компонента</label>
            <input
              value={componentId}
              onChange={e => setComponentId(e.target.value)}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono"
            />
          </div>
          <button
            type="button"
            disabled={discovering}
            onClick={runDiscover}
            className="text-sm bg-blue-600 text-white rounded px-4 py-2 hover:bg-blue-700 disabled:opacity-50"
          >
            {discovering ? "Запрос…" : "Запустить поиск"}
          </button>
        </div>
      </div>

      {err && <p className="text-sm text-red-600 mb-4">{err}</p>}

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Название</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Источник</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Полнота</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Сайт</th>
              <th className="text-right px-4 py-3 font-medium text-gray-600">Действия</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map(r => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{r.name}</td>
                <td className="px-4 py-3 text-gray-600">{r.source === "agent" ? "Агент" : "Заявка"}</td>
                <td className="px-4 py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${r.completeness === "complete" ? "bg-green-100 text-green-800" : "bg-amber-100 text-amber-800"}`}>
                    {r.completeness === "complete" ? "есть контакт" : "неполно"}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{r.email ?? "—"}</td>
                <td className="px-4 py-3 text-gray-500">
                  {r.website ? <a href={r.website} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{r.website}</a> : "—"}
                </td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button type="button" onClick={() => approve(r.id)} className="text-xs text-green-700 hover:underline">Одобрить</button>
                  <button type="button" onClick={() => reject(r.id)} className="text-xs text-red-600 hover:underline">Отклонить</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="p-6 text-center text-gray-500 text-sm">Нет кандидатов в статусе «ожидает»</p>}
      </div>
    </Layout>
  );
}
