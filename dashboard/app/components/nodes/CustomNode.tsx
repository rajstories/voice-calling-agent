import React from 'react';
import { Handle, Position } from 'reactflow';
import { Hand, HelpCircle, AlertCircle, Database } from 'lucide-react';

const iconMap: any = {
  Greeting: <Hand className="h-4 w-4 text-indigo-600" />,
  Discovery: <HelpCircle className="h-4 w-4 text-blue-600" />,
  Objection: <AlertCircle className="h-4 w-4 text-amber-600" />,
  RAG: <Database className="h-4 w-4 text-emerald-600" />,
};

const tintMap: any = {
  Greeting: 'bg-indigo-50 border-indigo-100',
  Discovery: 'bg-blue-50 border-blue-100',
  Objection: 'bg-amber-50 border-amber-100',
  RAG: 'bg-emerald-50 border-emerald-100',
};

export default function CustomNode({ data }: any) {
  const nodeType = data.type || 'Greeting';
  const label = data.label || 'Node';
  const icon = iconMap[nodeType] || iconMap['Greeting'];
  const tint = tintMap[nodeType] || tintMap['Greeting'];

  return (
    <div className="w-64 rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-400" />
      
      <div className={`flex items-center space-x-2 px-4 py-3 border-b ${tint}`}>
        <div className="flex h-6 w-6 items-center justify-center rounded bg-white shadow-sm">
          {icon}
        </div>
        <span className="text-sm font-semibold text-slate-800">{label}</span>
      </div>
      
      <div className="p-4">
        <label className="block text-xs font-medium text-slate-500 mb-1">
          AI Instructions
        </label>
        <textarea
          className="w-full resize-none rounded-md border border-slate-200 bg-slate-50 p-2 text-xs text-slate-700 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 placeholder:text-slate-400 nodrag"
          rows={3}
          placeholder={data.placeholder || "Enter instructions..."}
          defaultValue={data.instructions || ""}
        />
      </div>

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-indigo-500" />
    </div>
  );
}
