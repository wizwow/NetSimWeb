import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Cloud } from 'lucide-react';

export const CloudNode = memo(({ data }: NodeProps) => {
  return (
    <BaseNode 
      data={data as NetworkNode}
      icon={<Cloud size={22} color="var(--node-cloud)" />}
      handles={
        <>
          <Handle type="target" position={Position.Top} className="netsim-handle" id="top" />
          <Handle type="source" position={Position.Bottom} className="netsim-handle" id="bottom" />
        </>
      }
    />
  );
});
