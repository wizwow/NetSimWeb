import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Network } from 'lucide-react';

export const SwitchNode = memo(({ data, id }: NodeProps) => {
  return (
    <BaseNode
      nodeId={id}
      data={data as NetworkNode}
      iconBg="var(--dev-switch-bg)"
      icon={<Network size={26} color="var(--dev-switch)" />}
      handles={
        <>
          <Handle type="target" position={Position.Top} id="eth0" />
          <Handle type="source" position={Position.Right} id="eth1" />
          <Handle type="source" position={Position.Bottom} id="eth2" />
          <Handle type="target" position={Position.Left} id="eth3" />
        </>
      }
    />
  );
});
