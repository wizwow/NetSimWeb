import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Network } from 'lucide-react';

export const SwitchNode = memo(({ data }: NodeProps) => {
  return (
    <BaseNode 
      data={data as NetworkNode}
      icon={<Network size={22} color="var(--node-switch)" />}
      handles={
        <>
          <Handle type="target" position={Position.Top} className="netsim-handle" id="eth0" title="eth0" />
          <Handle type="source" position={Position.Right} className="netsim-handle" id="eth1" title="eth1" />
          <Handle type="source" position={Position.Bottom} className="netsim-handle" id="eth2" title="eth2" />
          <Handle type="target" position={Position.Left} className="netsim-handle" id="eth3" title="eth3" />
        </>
      }
    />
  );
});
