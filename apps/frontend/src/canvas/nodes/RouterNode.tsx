import { memo } from 'react';
import type { NodeProps } from '@xyflow/react';
import type { NetworkNode } from '@netsimflow/shared-types';
import { BaseNode } from './BaseNode';
import { Router } from 'lucide-react';

export const RouterNode = memo(({ data }: NodeProps) => (
  <BaseNode
    data={data as NetworkNode}
    icon={<Router size={22} color="var(--node-router)" />}
  />
));
