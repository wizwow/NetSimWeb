import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@octet/shared-types';
import { BaseNode } from './BaseNode';
import { Monitor } from 'lucide-react';

export const HostNode = memo(({ data }: NodeProps) => (
  <BaseNode
    data={data as NetworkNode}
    icon={<Monitor size={22} color="var(--node-host)" />}
  />
));
