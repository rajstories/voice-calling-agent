"use client";

import React, { useState, useCallback, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Hand, HelpCircle, AlertCircle, Database, Play } from 'lucide-react';
import CustomNode from '../components/nodes/CustomNode';

const nodeTypes = {
  custom: CustomNode,
};

const initialNodes = [
  {
    id: '1',
    type: 'custom',
    position: { x: 250, y: 150 },
    data: {
      type: 'Greeting',
      label: 'Greeting Node',
      placeholder: 'E.g., Hello, this is Raj from UPM Consultancy...',
    },
  },
];

const initialEdges: any[] = [];

let id = 10;
const getId = () => `dndnode_${id++}`;

function GraphifyCanvas() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [reactFlowInstance, setReactFlowInstance] = useState<any>(null);

  const onConnect = useCallback(
    (params: any) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragStart = (event: React.DragEvent, nodeType: string, label: string) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ type: nodeType, label }));
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
      const nodeDataStr = event.dataTransfer.getData('application/reactflow');
      
      if (!nodeDataStr) return;
      
      const nodeData = JSON.parse(nodeDataStr);

      if (typeof nodeData.type === 'undefined' || !nodeData.type) return;

      const position = reactFlowInstance?.project({
        x: event.clientX - (reactFlowBounds?.left || 0),
        y: event.clientY - (reactFlowBounds?.top || 0),
      });

      const newNode = {
        id: getId(),
        type: 'custom',
        position,
        data: {
          type: nodeData.type,
          label: nodeData.label,
          placeholder: 'Enter AI instructions...',
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  return (
    <div className="flex h-screen w-full flex-col">
      {/* Top Control Bar */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4 shadow-sm z-10">
        <h2 className="text-xl font-bold tracking-tight text-slate-900">
          UPM Solar Outbound Campaign
        </h2>
        <div className="flex items-center space-x-4">
          <button className="rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-200">
            Save Draft
          </button>
          <button className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
            <Play className="mr-2 h-4 w-4 animate-pulse" />
            Deploy to LiveKit
          </button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Node Toolkit Panel (Left Sidebar) */}
        <aside className="w-72 flex-shrink-0 border-r border-slate-800 bg-slate-950 p-6 flex flex-col z-10">
          <h3 className="mb-2 text-lg font-semibold text-slate-100">Node Toolkit</h3>
          <p className="mb-6 text-xs text-slate-400">
            Drag these state blocks onto the canvas to build your conversational flow.
          </p>

          <div className="space-y-4">
            <div
              className="flex cursor-grab items-center space-x-3 rounded-lg border border-slate-800 bg-slate-900 p-3 transition-colors hover:border-indigo-500 hover:bg-slate-800 active:cursor-grabbing"
              onDragStart={(e) => onDragStart(e, 'Greeting', 'Greeting Node')}
              draggable
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-500/10">
                <Hand className="h-5 w-5 text-indigo-400" />
              </div>
              <span className="text-sm font-medium text-slate-200">Greeting Node</span>
            </div>

            <div
              className="flex cursor-grab items-center space-x-3 rounded-lg border border-slate-800 bg-slate-900 p-3 transition-colors hover:border-blue-500 hover:bg-slate-800 active:cursor-grabbing"
              onDragStart={(e) => onDragStart(e, 'Discovery', 'Discovery Node')}
              draggable
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-500/10">
                <HelpCircle className="h-5 w-5 text-blue-400" />
              </div>
              <span className="text-sm font-medium text-slate-200">Discovery Node</span>
            </div>

            <div
              className="flex cursor-grab items-center space-x-3 rounded-lg border border-slate-800 bg-slate-900 p-3 transition-colors hover:border-amber-500 hover:bg-slate-800 active:cursor-grabbing"
              onDragStart={(e) => onDragStart(e, 'Objection', 'Objection Node')}
              draggable
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-500/10">
                <AlertCircle className="h-5 w-5 text-amber-400" />
              </div>
              <span className="text-sm font-medium text-slate-200">Objection Node</span>
            </div>

            <div
              className="flex cursor-grab items-center space-x-3 rounded-lg border border-slate-800 bg-slate-900 p-3 transition-colors hover:border-emerald-500 hover:bg-slate-800 active:cursor-grabbing"
              onDragStart={(e) => onDragStart(e, 'RAG', 'RAG Knowledge Lookup')}
              draggable
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-500/10">
                <Database className="h-5 w-5 text-emerald-400" />
              </div>
              <span className="text-sm font-medium text-slate-200">RAG Knowledge Lookup</span>
            </div>
          </div>
        </aside>

        {/* Main Canvas */}
        <main className="flex-1 relative" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            className="bg-slate-50"
            fitView
          >
            <Background color="#cbd5e1" gap={16} size={1} />
            <Controls className="bg-white fill-slate-700 shadow-sm border border-slate-200 rounded-md" />
            <MiniMap 
              className="bg-white border border-slate-200 rounded-md shadow-sm"
              maskColor="rgba(248, 250, 252, 0.7)"
              nodeColor="#e2e8f0"
            />
          </ReactFlow>
        </main>
      </div>
    </div>
  );
}

export default function GraphifyPage() {
  return (
    <ReactFlowProvider>
      <GraphifyCanvas />
    </ReactFlowProvider>
  );
}
