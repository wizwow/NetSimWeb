import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Router } from 'lucide-react';

export const RouterNode = memo(({ data }: NodeProps) => {
  return (
    <BaseNode 
      data={data as NetworkNode}
      icon={<Router size={22} color="var(--node-router)" />}
      handles={
        <>
          <Handle type="source" position={Position.Top} className="netsim-handle" id="top" />
          <Handle type="source" position={Position.Right} className="netsim-handle" id="right" />
          <Handle type="source" position={Position.Bottom} className="netsim-handle" id="bottom" />
          <Handle type="source" position={Position.Left} className="netsim-handle" id="left" />
        </>
      }
    />
  );
});
