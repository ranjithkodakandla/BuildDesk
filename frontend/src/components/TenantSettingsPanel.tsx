/**
 * TenantSettingsPanel — Company info for PDF header.
 *
 * Stores extra fields (address, phone, drawn_by) in standard_notes as JSON
 * so we don't need a DB migration.  The PDF generator reads these fields.
 */
import React, { useEffect, useState } from 'react';
import { TenantProfile, tenantApi } from '../api/tenant';

interface CompanyExtra {
  address1:  string;
  address2:  string;
  phone:     string;
  drawn_by:  string;
}

function parseExtra(raw: string | undefined): CompanyExtra {
  try {
    const parsed = JSON.parse(raw ?? '{}');
    return {
      address1: parsed.address1  ?? '',
      address2: parsed.address2  ?? '',
      phone:    parsed.phone     ?? '',
      drawn_by: parsed.drawn_by  ?? '',
    };
  } catch {
    return { address1: '', address2: '', phone: '', drawn_by: '' };
  }
}

export const TenantSettingsPanel: React.FC = () => {
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [extra, setExtra]     = useState<CompanyExtra>({ address1: '', address2: '', phone: '', drawn_by: '' });
  const [saving, setSaving]   = useState(false);
  const [saved, setSaved]     = useState(false);

  useEffect(() => {
    tenantApi.getProfile().then(p => {
      setProfile(p);
      setExtra(parseExtra(p.standard_notes));
    }).catch(console.error);
  }, []);

  const updateField = (key: keyof TenantProfile, value: string) => {
    if (!profile) return;
    setProfile({ ...profile, [key]: value });
  };

  const updateExtra = (key: keyof CompanyExtra, value: string) => {
    setExtra(prev => ({ ...prev, [key]: value }));
  };

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    setSaved(false);
    try {
      const saved_p = await tenantApi.updateProfile({
        company_name:   profile.company_name || undefined,
        logo_url:       profile.logo_url     || undefined,
        default_footer: profile.default_footer || undefined,
        standard_notes: JSON.stringify(extra),
      });
      setProfile(saved_p);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  };

  if (!profile) {
    return (
      <section className="bg-white border border-[#e2e8f0] rounded p-5 text-sm text-[#94a3b8]">
        Loading…
      </section>
    );
  }

  return (
    <section className="bg-white border border-[#e2e8f0] rounded p-5 space-y-5 max-w-2xl">
      <div>
        <h2 className="text-sm font-bold text-[#1e293b] mb-1">Company Settings</h2>
        <p className="text-xs text-[#94a3b8]">
          These fields print on every shop drawing PDF. Set them once.
        </p>
      </div>

      {/* Company identity */}
      <fieldset className="space-y-3">
        <legend className="text-xs font-bold text-[#475569] uppercase tracking-wider">
          Company Info — appears on every PDF header
        </legend>

        <label className="block">
          <span className="label-text">Company Name</span>
          <input
            className="input-field"
            value={profile.company_name ?? ''}
            placeholder="e.g. Virgin Surfaces"
            onChange={e => updateField('company_name', e.target.value)}
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="label-text">Address Line 1</span>
            <input
              className="input-field"
              value={extra.address1}
              placeholder="5325 Merchandise Drive"
              onChange={e => updateExtra('address1', e.target.value)}
            />
          </label>
          <label className="block">
            <span className="label-text">Address Line 2</span>
            <input
              className="input-field"
              value={extra.address2}
              placeholder="Fort Wayne, IN 46825"
              onChange={e => updateExtra('address2', e.target.value)}
            />
          </label>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="label-text">Phone</span>
            <input
              className="input-field"
              value={extra.phone}
              placeholder="260-888-7102"
              onChange={e => updateExtra('phone', e.target.value)}
            />
          </label>
          <label className="block">
            <span className="label-text">Default Drawn By</span>
            <input
              className="input-field"
              value={extra.drawn_by}
              placeholder="Omer Vinson"
              onChange={e => updateExtra('drawn_by', e.target.value)}
            />
          </label>
        </div>
      </fieldset>

      <div className="flex items-center gap-3">
        <button
          onClick={save}
          disabled={saving}
          className="btn-primary px-5 py-2 text-sm disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
        {saved && (
          <span className="text-xs text-[#047857] font-medium">✓ Saved</span>
        )}
      </div>
    </section>
  );
};
