import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@octet/shared-types';
import { BaseNode } from './BaseNode';
import { Cloud } from 'lucide-react';

export const CloudNode = memo(({ data }: NodeProps) => (
  <BaseNode
    data={data as NetworkNode}
    icon={<Cloud size={22} color="var(--node-cloud)" />}
  />
));
