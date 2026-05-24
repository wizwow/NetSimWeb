import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Monitor } from 'lucide-react';

export const HostNode = memo(({ data }: NodeProps) => {
  return (
    <BaseNode 
      data={data as NetworkNode}
      icon={<Monitor size={22} color="var(--node-host)" />}
      handles={
        <>
          <Handle type="target" position={Position.Top} className="netsim-handle" id="top" />
          <Handle type="source" position={Position.Bottom} className="netsim-handle" id="bottom" />
        </>
      }
    />
  );
});
