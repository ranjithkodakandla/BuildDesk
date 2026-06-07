import React from 'react';

/**
 * Placeholder for the upcoming StoneDesk-style Matrix Mode project setup.
 * Shown inside the Basic Builder panel to signal the coming feature.
 */
export const MatrixModePlaceholder: React.FC = () => (
  <div className="rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 px-6 py-8 text-center">
    <div className="text-3xl mb-3">📊</div>
    <h3 className="font-semibold text-gray-700 text-sm mb-1">Project Setup</h3>
    <p className="text-xs text-gray-500 max-w-xs mx-auto">
      Matrix Mode is coming next — enter all units, floors, and types in one
      spreadsheet-style grid. No more unit-by-unit setup.
    </p>
    <div className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-gray-200 text-xs text-gray-500 font-medium">
      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
      Coming next
    </div>
  </div>
);
