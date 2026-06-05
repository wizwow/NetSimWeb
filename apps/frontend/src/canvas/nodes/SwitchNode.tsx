import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@octet/shared-types';
import { BaseNode } from './BaseNode';
import { Network } from 'lucide-react';

export const SwitchNode = memo(({ data }: NodeProps) => (
  <BaseNode
    data={data as NetworkNode}
    icon={<Network size={22} color="var(--node-switch)" />}
  />
));
