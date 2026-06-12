"use client";

import React, { useState } from 'react';
import { UploadCloud, FileText, Trash2, Search, CheckCircle, Upload } from 'lucide-react';

interface Document {
  id: string;
  name: string;
  date: string;
  chunks: string;
  status: string;
}

export default function KnowledgeVaultPage() {
  const [documents, setDocuments] = useState<Document[]>([
    {
      id: '1',
      name: 'Tata_SPG_Price_List_June_2026.pdf',
      date: 'June 10, 2026',
      chunks: '124 Chunks',
      status: 'Indexed & Active',
    },
    {
      id: '2',
      name: 'Objection_Handling_Playbook.md',
      date: 'June 11, 2026',
      chunks: '58 Chunks',
      status: 'Indexed & Active',
    },
  ]);

  const [query, setQuery] = useState('What is the price of a 5kW system?');
  const [retrievedChunk, setRetrievedChunk] = useState('₹204,800 for RCC Roof');
  const [retrievedSource, setRetrievedSource] = useState('Tata_SPG_Price_List_June_2026.pdf (Chunk #42)');
  const [isUploading, setIsUploading] = useState(false);

  const handleDelete = (id: string) => {
    setDocuments(documents.filter((doc) => doc.id !== id));
  };

  const handleUpload = () => {
    setIsUploading(true);
    setTimeout(() => {
      const newDoc: Document = {
        id: Date.now().toString(),
        name: `Solar_Installation_FAQ_${Math.floor(Math.random() * 1000)}.pdf`,
        date: new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }),
        chunks: `${Math.floor(Math.random() * 80) + 20} Chunks`,
        status: 'Indexed & Active',
      };
      setDocuments((prev) => [...prev, newDoc]);
      setIsUploading(false);
    }, 1200);
  };

  const handleTestQuery = () => {
    const q = query.toLowerCase();
    if (q.includes('price') || q.includes('cost') || q.includes('5kw')) {
      setRetrievedChunk('₹204,800 for RCC Roof. Includes panel installation, structure wiring, and net metering setup.');
      setRetrievedSource('Tata_SPG_Price_List_June_2026.pdf (Chunk #42)');
    } else if (q.includes('objection') || q.includes('expensive') || q.includes('convince')) {
      setRetrievedChunk('When customer says "solar is too expensive", pivot to financing options. Emphasize payback period of 4.2 years.');
      setRetrievedSource('Objection_Handling_Playbook.md (Chunk #12)');
    } else {
      setRetrievedChunk('Solar panels have a performance warranty of 25 years. Tata modules offer 10 years product warranty.');
      setRetrievedSource('Tata_SPG_Price_List_June_2026.pdf (Chunk #8)');
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight text-slate-900">Knowledge Vault</h2>
      </div>

      {/* Top Section: Upload Zone */}
      <section className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-10 text-center shadow-sm transition-all hover:border-indigo-400">
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-indigo-50">
          <UploadCloud className="h-10 w-10 text-indigo-500" />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-slate-900">Upload Knowledge Documents</h3>
        <p className="mt-2 text-sm text-slate-500">
          Drag & drop your sales playbooks, pricing matrices, or FAQs here
        </p>
        <div className="mt-6">
          <button 
            onClick={handleUpload}
            disabled={isUploading}
            className="inline-flex items-center justify-center rounded-md bg-indigo-600 px-6 py-3 text-sm font-medium text-white shadow transition-colors hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-indigo-700 disabled:pointer-events-none disabled:opacity-50"
          >
            {isUploading ? 'Uploading & Indexing...' : 'Browse Files'}
          </button>
        </div>
      </section>

      {/* Bottom Section: 2 Columns */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        
        {/* Active Document Library */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm lg:col-span-2">
          <div className="border-b border-slate-100 p-6">
            <h3 className="text-lg font-semibold text-slate-900">Active Document Library</h3>
            <p className="text-sm text-slate-500">Manage and view your currently indexed files.</p>
          </div>
          <div className="p-0">
            <div className="relative w-full overflow-auto">
              <table className="w-full caption-bottom text-sm">
                <thead className="[&_tr]:border-b [&_tr]:border-slate-200">
                  <tr className="border-b transition-colors hover:bg-slate-100/50">
                    <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Document Name</th>
                    <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Upload Date</th>
                    <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Chunk Count</th>
                    <th className="h-12 px-6 text-left align-middle font-medium text-slate-500">Status</th>
                    <th className="h-12 px-6 text-right align-middle font-medium text-slate-500">Actions</th>
                  </tr>
                </thead>
                <tbody className="[&_tr:last-child]:border-0">
                  {documents.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-slate-500">
                        No documents indexed. Upload a file above.
                      </td>
                    </tr>
                  ) : (
                    documents.map((doc) => (
                      <tr key={doc.id} className="border-b border-slate-100 transition-colors hover:bg-slate-50/50">
                        <td className="p-6 align-middle">
                          <div className="flex items-center space-x-3">
                            <FileText className="h-5 w-5 text-indigo-500" />
                            <span className="font-medium text-slate-900">{doc.name}</span>
                          </div>
                        </td>
                        <td className="p-6 align-middle text-slate-600">{doc.date}</td>
                        <td className="p-6 align-middle text-slate-600">{doc.chunks}</td>
                        <td className="p-6 align-middle">
                          <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
                            <CheckCircle className="mr-1 h-3 w-3" />
                            {doc.status}
                          </span>
                        </td>
                        <td className="p-6 align-middle text-right">
                          <button 
                            onClick={() => handleDelete(doc.id)}
                            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                            <span className="sr-only">Delete</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* Test Retrieval Sandbox */}
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm lg:col-span-1">
          <div className="border-b border-slate-100 p-6">
            <h3 className="flex items-center space-x-2 text-lg font-semibold text-slate-900">
              <Search className="h-5 w-5 text-indigo-600" />
              <span>Test Retrieval Sandbox</span>
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Type a customer question to see exactly what data the AI will fetch.
            </p>
          </div>
          <div className="flex flex-col space-y-4 p-6">
            <div className="space-y-2">
              <label htmlFor="query" className="text-sm font-medium leading-none text-slate-700">
                Customer Query
              </label>
              <input
                id="query"
                className="flex h-10 w-full rounded-md border border-slate-300 bg-transparent px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-600 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="e.g. What is the price of a 5kW system?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <button 
              onClick={handleTestQuery}
              className="inline-flex w-full items-center justify-center rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-slate-950 disabled:pointer-events-none disabled:opacity-50 transition-colors"
            >
              Test Query
            </button>

            <div className="mt-4 rounded-lg bg-slate-50 p-4 border border-slate-100">
              <div className="mb-2 flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <span>RAG Retrieval Result</span>
                <span className="text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full">Success</span>
              </div>
              <div className="space-y-3 text-sm">
                <div>
                  <span className="font-semibold text-slate-700">Query: </span>
                  <span className="text-slate-600">{query}</span>
                </div>
                <div>
                  <span className="font-semibold text-slate-700">Retrieved Chunk: </span>
                  <p className="mt-1 rounded border border-indigo-100 bg-indigo-50/50 p-3 text-slate-800 leading-relaxed">
                    {retrievedChunk}
                  </p>
                </div>
                <div className="text-xs text-slate-500 pt-2 border-t border-slate-200">
                  Source: {retrievedSource}
                </div>
              </div>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
