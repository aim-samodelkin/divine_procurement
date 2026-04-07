"use client";
import { useState } from "react";

export interface CategoryNode {
  id: string;
  name: string;
  description: string | null;
  parent_id: string | null;
  is_leaf: boolean;
  children: CategoryNode[];
}

interface Props {
  nodes: CategoryNode[];
  onAdd: (parentId: string | null) => void;
  onDelete: (id: string) => void;
  depth?: number;
}

export function CategoryTree({ nodes, onAdd, onDelete, depth = 0 }: Props) {
  return (
    <ul className={depth > 0 ? "ml-4 border-l border-gray-200 pl-3" : ""}>
      {nodes.map(node => (
        <CategoryNodeItem key={node.id} node={node} onAdd={onAdd} onDelete={onDelete} depth={depth} />
      ))}
      <li>
        <button
          onClick={() => onAdd(depth === 0 ? null : nodes[0]?.parent_id ?? null)}
          className="text-sm text-blue-600 hover:text-blue-800 py-1"
        >
          + Добавить {depth === 0 ? "категорию" : "подкатегорию"}
        </button>
      </li>
    </ul>
  );
}

function CategoryNodeItem({ node, onAdd, onDelete, depth }: { node: CategoryNode; onAdd: (id: string | null) => void; onDelete: (id: string) => void; depth: number }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <li className="py-1">
      <div className="flex items-center gap-2 group">
        {node.children.length > 0 && (
          <button onClick={() => setExpanded(!expanded)} className="text-gray-400 hover:text-gray-600 text-xs w-4">
            {expanded ? "▼" : "▶"}
          </button>
        )}
        {node.children.length === 0 && <span className="w-4" />}
        <span className={`text-sm ${node.is_leaf ? "text-gray-900" : "font-medium text-gray-700"}`}>{node.name}</span>
        {node.is_leaf && <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">лист</span>}
        <div className="hidden group-hover:flex items-center gap-1 ml-auto">
          <button onClick={() => onAdd(node.id)} className="text-xs text-blue-600 hover:text-blue-800">+ суб</button>
          {node.is_leaf && (
            <button onClick={() => onDelete(node.id)} className="text-xs text-red-500 hover:text-red-700">удалить</button>
          )}
        </div>
      </div>
      {expanded && node.children.length > 0 && (
        <CategoryTree nodes={node.children} onAdd={onAdd} onDelete={onDelete} depth={depth + 1} />
      )}
    </li>
  );
}
