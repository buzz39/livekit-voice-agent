import React, { useEffect, useState } from 'react';
import { Building2, Plus, Trash2, X, CheckCircle, AlertCircle } from 'lucide-react';
import { deleteTenant, getTenants, upsertTenant } from '../../api';

const emptyForm = {
  tenant_id: '',
  display_name: '',
  agent_slug: '',
  workflow_policy: '',
  opening_line: '',
  api_key: '',
  is_active: true,
};

export default function TenantManager() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [toast, setToast] = useState(null);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const load = async () => {
    setLoading(true);
    const list = await getTenants(false, 200);
    setTenants(Array.isArray(list) ? list : []);
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setForm(emptyForm);
    setShowForm(true);
  };

  const openEdit = (tenant) => {
    setForm({
      tenant_id: tenant.tenant_id || '',
      display_name: tenant.display_name || '',
      agent_slug: tenant.agent_slug || '',
      workflow_policy: tenant.workflow_policy || '',
      opening_line: tenant.opening_line || '',
      api_key: '',
      is_active: tenant.is_active !== false,
    });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.tenant_id.trim()) {
      showToast('tenant_id is required', 'error');
      return;
    }

    try {
      await upsertTenant({
        ...form,
        tenant_id: form.tenant_id.trim(),
        display_name: form.display_name.trim(),
        agent_slug: form.agent_slug.trim(),
        workflow_policy: form.workflow_policy.trim(),
        opening_line: form.opening_line.trim(),
      });
      showToast('Tenant saved');
      setShowForm(false);
      await load();
    } catch {
      showToast('Failed to save tenant', 'error');
    }
  };

  const handleDelete = async (tenantId) => {
    if (!window.confirm(`Delete tenant ${tenantId}?`)) return;
    try {
      await deleteTenant(tenantId);
      showToast('Tenant deleted');
      await load();
    } catch {
      showToast('Failed to delete tenant', 'error');
    }
  };

  return (
    <div className="flex flex-col h-full gap-4">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-2 rounded-lg text-sm border ${
          toast.type === 'error'
            ? 'bg-red-500/10 border-red-500/30 text-red-300'
            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
        }`}>
          {toast.type === 'error' ? <AlertCircle size={14} /> : <CheckCircle size={14} />}
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-bold text-white">Tenants</h2>
          <p className="text-sm text-slate-400">Manage tenant routing, workflow, and voice behavior settings.</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium text-white"
        >
          <Plus size={16} /> Add Tenant
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2">
        {loading ? (
          <div className="text-slate-500 text-sm text-center py-8">Loading tenants...</div>
        ) : tenants.length === 0 ? (
          <div className="text-slate-500 text-sm text-center py-8">No tenants configured yet.</div>
        ) : (
          tenants.map((tenant) => (
            <div key={tenant.tenant_id} className="bg-slate-900 border border-slate-800 rounded-lg p-4 hover:border-slate-600 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Building2 size={14} className="text-indigo-400" />
                    <span className="text-sm font-semibold text-white">{tenant.tenant_id}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${tenant.is_active ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' : 'bg-slate-600/20 border-slate-500/40 text-slate-400'}`}>
                      {tenant.is_active ? 'active' : 'inactive'}
                    </span>
                  </div>
                  {tenant.display_name && <p className="text-xs text-slate-300 mt-1">{tenant.display_name}</p>}
                  <div className="text-xs text-slate-500 mt-2 space-y-1">
                    <div>agent: {tenant.agent_slug || '-'}</div>
                    <div>workflow: {tenant.workflow_policy || '-'}</div>
                  </div>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(tenant)} className="px-2 py-1 rounded text-xs bg-slate-800 hover:bg-slate-700 text-slate-200">Edit</button>
                  <button onClick={() => handleDelete(tenant.tenant_id)} className="p-1 rounded hover:bg-slate-700 text-slate-400 hover:text-red-400">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="relative bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 sticky top-0 bg-slate-900 z-10">
              <h3 className="text-white font-semibold">Tenant Configuration</h3>
              <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-white p-1"><X size={18} /></button>
            </div>
            <div className="px-5 py-4 space-y-3">
              <Field label="Tenant ID" required>
                <input value={form.tenant_id} onChange={(e) => setForm((f) => ({ ...f, tenant_id: e.target.value }))} placeholder="acme-roofing" className={inputClass} />
              </Field>
              <Field label="Display Name">
                <input value={form.display_name} onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))} placeholder="Acme Roofing" className={inputClass} />
              </Field>
              <Field label="Agent Slug">
                <input value={form.agent_slug} onChange={(e) => setForm((f) => ({ ...f, agent_slug: e.target.value }))} placeholder="default_roofing_agent" className={inputClass} />
              </Field>
              <Field label="Workflow Policy">
                <input value={form.workflow_policy} onChange={(e) => setForm((f) => ({ ...f, workflow_policy: e.target.value }))} placeholder="standard" className={inputClass} />
              </Field>
              <Field label="Opening Line Override">
                <textarea value={form.opening_line} onChange={(e) => setForm((f) => ({ ...f, opening_line: e.target.value }))} rows={3} className={inputClass} />
              </Field>
              <Field label="API Key (optional)">
                <input value={form.api_key} onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))} placeholder="tenant-scoped key" className={inputClass} />
              </Field>
              <label className="flex items-center gap-2 text-sm text-slate-300 mt-1">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="rounded border-slate-600 bg-slate-800"
                />
                Active
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <button onClick={() => setShowForm(false)} className={btnSecondary}>Cancel</button>
                <button onClick={handleSave} className={btnPrimary}>Save Tenant</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const inputClass = 'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500';
const btnPrimary = 'px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-sm font-medium text-white transition-colors';
const btnSecondary = 'px-4 py-2 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors';

function Field({ label, required, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-1">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      {children}
    </div>
  );
}
