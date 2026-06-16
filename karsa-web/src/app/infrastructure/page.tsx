'use client';

import React from 'react';
import { PageHeader } from '../../components/shared/PageHeader';

export default function InfrastructureWorkspace() {
  return (
    <>
      <PageHeader title="Infrastructure Workspace" description="Platform Operations and Limits" />
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6">
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32">
          <h3 className="font-semibold text-slate-600">Provider Status</h3>
          <span className="text-2xl font-bold text-green-600">Operational</span>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32">
          <h3 className="font-semibold text-slate-600">Capability Status</h3>
          <span className="text-2xl font-bold text-green-600">Active</span>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32">
          <h3 className="font-semibold text-slate-600">Queue Status</h3>
          <span className="text-2xl font-bold text-slate-800 dark:text-slate-200">0 pending</span>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32">
          <h3 className="font-semibold text-slate-600">Worker Status</h3>
          <span className="text-2xl font-bold text-green-600">Healthy</span>
        </div>
        <div className="border rounded-xl p-4 bg-white dark:bg-slate-900 shadow-sm flex flex-col justify-between h-32 lg:col-span-2">
          <h3 className="font-semibold text-slate-600">System Health</h3>
          <span className="text-sm text-slate-500 mt-2">All platform services are running nominally within configured limits.</span>
        </div>
      </div>
    </>
  );
}
