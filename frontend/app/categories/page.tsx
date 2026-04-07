"use client";
import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { CategoryTree, CategoryNode } from "../components/CategoryTree";
import { apiFetch } from "../lib/api";

export default function CategoriesPage() {
  const [tree, setTree] = useState<CategoryNode[]>([]);
  const [adding, setAdding] = useState<{ parentId: string | null } | null>(null);
  const [newName, setNewName] = useState("");

  const load = () => apiFetch<CategoryNode[]>("/categories/tree").then(setTree);
  useEffect(() => { load(); }, []);

  const handleAdd = async (parentId: string | null) => {
    setAdding({ parentId });
    setNewName("");
  };

  const submitAdd = async () => {
    if (!newName.trim()) return;
    await apiFetch("/categories", {
      method: "POST",
      body: JSON.stringify({ name: newName.trim(), parent_id: adding?.parentId }),
    });
    setAdding(null);
    load();
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Удалить категорию?")) return;
    await apiFetch(`/categories/${id}`, { method: "DELETE" });
    load();
  };

  return (
    <Layout>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Категории</h1>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 p-4 max-w-xl">
        <CategoryTree nodes={tree} onAdd={handleAdd} onDelete={handleDelete} />
      </div>
      {adding !== null && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-80 space-y-3 shadow-xl">
            <h3 className="font-semibold">Новая категория</h3>
            <input
              autoFocus value={newName} onChange={e => setNewName(e.target.value)}
              onKeyDown={e => e.key === "Enter" && submitAdd()}
              placeholder="Название" className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setAdding(null)} className="text-sm text-gray-500 px-3 py-1.5 hover:bg-gray-100 rounded">Отмена</button>
              <button onClick={submitAdd} className="text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700">Создать</button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
