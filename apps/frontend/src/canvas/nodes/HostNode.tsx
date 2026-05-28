import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Monitor } from 'lucide-react';

export const HostNode = memo(({ data, id }: NodeProps) => {
  return (
    <BaseNode
      nodeId={id}
      data={data as NetworkNode}
      iconBg="var(--dev-host-bg)"
      icon={<Monitor size={26} color="var(--dev-host)" />}
      handles={
        <>
          <Handle type="target" position={Position.Top} id="eth0" />
          <Handle type="source" position={Position.Bottom} id="eth1" />
        </>
      }
    />
  );
});
