import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Network } from 'lucide-react';

export const SwitchNode = memo(({ data }: NodeProps<NetworkNode>) => {
  return (
    <BaseNode 
      data={data}
      icon={<Network size={22} color="var(--node-switch)" />}
      handles={
        <>
          <Handle type="target" position={Position.Top} className="netsim-handle" id="top" />
          <Handle type="source" position={Position.Right} className="netsim-handle" id="right" />
          <Handle type="source" position={Position.Bottom} className="netsim-handle" id="bottom" />
          <Handle type="target" position={Position.Left} className="netsim-handle" id="left" />
        </>
      }
    />
  );
});
