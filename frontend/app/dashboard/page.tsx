"use client";
import { useEffect, useState } from "react";
import Layout from "../components/Layout";
import { apiFetch } from "../lib/api";

interface CoverageItem { category_name: string; supplier_count: number; status: string; }

export default function DashboardPage() {
  const [coverage, setCoverage] = useState<CoverageItem[]>([]);

  useEffect(() => {
    apiFetch<CoverageItem[]>("/suppliers/coverage").then(setCoverage).catch(console.error);
  }, []);

  const redCount = coverage.filter(c => c.status === "red").length;
  const yellowCount = coverage.filter(c => c.status === "yellow").length;

  return (
    <Layout>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Дашборд</h1>
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Категорий без поставщиков</div>
          <div className="text-3xl font-bold text-red-600 mt-1">{redCount}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Категорий с малым покрытием</div>
          <div className="text-3xl font-bold text-yellow-500 mt-1">{yellowCount}</div>
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm text-gray-500">Категорий всего</div>
          <div className="text-3xl font-bold text-gray-900 mt-1">{coverage.length}</div>
        </div>
      </div>
      {redCount > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          Категории без поставщиков: {coverage.filter(c => c.status === "red").map(c => c.category_name).join(", ")}
        </div>
      )}
    </Layout>
  );
}
