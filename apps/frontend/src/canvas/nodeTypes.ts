import type { NodeTypes } from '@xyflow/react';
import { RouterNode } from './nodes/RouterNode';
import { SwitchNode } from './nodes/SwitchNode';
import { CloudNode } from './nodes/CloudNode';
import { HostNode } from './nodes/HostNode';

export const nodeTypes: NodeTypes = {
  router: RouterNode as NodeTypes[string],
  switch: SwitchNode as NodeTypes[string],
  cloud: CloudNode as NodeTypes[string],
  host: HostNode as NodeTypes[string],
};
