import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Cloud } from 'lucide-react';

export const CloudNode = memo(({ data }: NodeProps<NetworkNode>) => {
  return (
    <BaseNode 
      data={data}
      icon={<Cloud size={22} color="var(--node-cloud)" />}
      handles={
        <>
          <Handle type="source" position={Position.Bottom} className="netsim-handle" id="bottom" />
        </>
      }
    />
  );
});
