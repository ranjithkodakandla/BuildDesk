import React, { useEffect, useState } from 'react';
import { TenantProfile, tenantApi } from '../api/tenant';

export const TenantSettingsPanel: React.FC = () => {
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    tenantApi.getProfile().then(setProfile).catch(console.error);
  }, []);

  const updateField = (key: keyof TenantProfile, value: string) => {
    if (!profile) return;
    setProfile({ ...profile, [key]: value });
  };

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    try {
      const saved = await tenantApi.updateProfile({
        company_name: profile.company_name || undefined,
        logo_url: profile.logo_url || undefined,
        default_footer: profile.default_footer || undefined,
        standard_notes: profile.standard_notes || undefined,
      });
      setProfile(saved);
    } finally {
      setSaving(false);
    }
  };

  if (!profile) {
    return <section className="bg-white border border-gray-200 rounded-lg p-5 text-sm text-gray-500">Loading tenant settings...</section>;
  }

  return (
    <section className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="text-sm">
          <span className="block font-medium text-gray-700 mb-1">Company name</span>
          <input className="w-full border border-gray-300 rounded-md px-3 py-2" value={profile.company_name || ''} onChange={(e) => updateField('company_name', e.target.value)} />
        </label>
        <label className="text-sm">
          <span className="block font-medium text-gray-700 mb-1">Logo placeholder URL</span>
          <input className="w-full border border-gray-300 rounded-md px-3 py-2" value={profile.logo_url || ''} onChange={(e) => updateField('logo_url', e.target.value)} />
        </label>
        <label className="text-sm md:col-span-2">
          <span className="block font-medium text-gray-700 mb-1">PDF footer</span>
          <input className="w-full border border-gray-300 rounded-md px-3 py-2" value={profile.default_footer || ''} onChange={(e) => updateField('default_footer', e.target.value)} />
        </label>
        <label className="text-sm md:col-span-2">
          <span className="block font-medium text-gray-700 mb-1">Standard fabrication notes</span>
          <textarea className="w-full border border-gray-300 rounded-md px-3 py-2 min-h-24" value={profile.standard_notes || ''} onChange={(e) => updateField('standard_notes', e.target.value)} />
        </label>
      </div>
      <div className="mt-4 flex justify-end">
        <button onClick={save} className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium">
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </section>
  );
};
