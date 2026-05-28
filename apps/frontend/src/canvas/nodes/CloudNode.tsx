import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Cloud } from 'lucide-react';

export const CloudNode = memo(({ data, id }: NodeProps) => {
  return (
    <BaseNode
      nodeId={id}
      data={data as NetworkNode}
      iconBg="var(--dev-cloud-bg)"
      icon={<Cloud size={26} color="var(--dev-cloud)" />}
      handles={
        <>
          <Handle type="target" position={Position.Top} id="eth0" />
          <Handle type="source" position={Position.Bottom} id="eth1" />
        </>
      }
    />
  );
});
