"use client";
import { useState } from "react";
import { ApiError, apiFetch } from "../../lib/api";

const TOKEN = process.env.NEXT_PUBLIC_SUPPLIER_REGISTRATION_TOKEN ?? "";

export default function PublicSupplierRegisterPage() {
  const [form, setForm] = useState({
    name: "",
    type: "company",
    email: "",
    website: "",
    phone: "",
    notes: "",
  });
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const submit = async () => {
    setErr(null);
    setMsg(null);
    if (!TOKEN) {
      setErr("Не задан NEXT_PUBLIC_SUPPLIER_REGISTRATION_TOKEN");
      return;
    }
    setSending(true);
    try {
      await apiFetch("/public/supplier-registration", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          type: form.type,
          email: form.email || null,
          website: form.website || null,
          phone: form.phone || null,
          notes: form.notes || null,
          category_ids: [],
        }),
        headers: {
          "X-Registration-Token": TOKEN,
        },
        skipAuthRedirect: true,
      });
      setMsg("Заявка отправлена. Менеджер свяжется с вами или уточнит категории.");
      setForm({ name: "", type: "company", email: "", website: "", phone: "", notes: "" });
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-xl border border-gray-200 shadow-sm p-8">
        <h1 className="text-xl font-semibold text-gray-900 mb-1">Регистрация поставщика</h1>
        <p className="text-sm text-gray-500 mb-6">
          Категории поставки можно уточнить с менеджером после заявки.
        </p>
        <div className="space-y-3">
          {[
            { label: "Название организации", key: "name", type: "text", required: true },
            { label: "Email", key: "email", type: "email" },
            { label: "Сайт", key: "website", type: "url" },
            { label: "Телефон", key: "phone", type: "tel" },
          ].map(f => (
            <div key={f.key}>
              <label className="block text-sm text-gray-600 mb-1">{f.label}</label>
              <input
                type={f.type}
                required={!!(f as { required?: boolean }).required}
                value={(form as Record<string, string>)[f.key]}
                onChange={e => setForm(prev => ({ ...prev, [f.key]: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              />
            </div>
          ))}
          <div>
            <label className="block text-sm text-gray-600 mb-1">Тип</label>
            <select
              value={form.type}
              onChange={e => setForm(prev => ({ ...prev, type: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="company">Компания</option>
              <option value="marketplace">Площадка</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Комментарий</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))}
              rows={3}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        {err && <p className="text-sm text-red-600 mt-4">{err}</p>}
        {msg && <p className="text-sm text-green-700 mt-4">{msg}</p>}
        <button
          type="button"
          disabled={sending || !form.name.trim()}
          onClick={submit}
          className="mt-6 w-full bg-blue-600 text-white rounded-lg py-2.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {sending ? "Отправка…" : "Отправить"}
        </button>
      </div>
    </div>
  );
}
