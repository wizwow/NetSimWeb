import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Monitor } from 'lucide-react';

export const HostNode = memo(({ data }: NodeProps<NetworkNode>) => {
  return (
    <BaseNode 
      data={data}
      icon={<Monitor size={22} color="var(--node-host)" />}
      handles={
        <>
          <Handle type="target" position={Position.Top} className="netsim-handle" id="top" />
        </>
      }
    />
  );
});
