import { RouterNode } from './nodes/RouterNode';
import { SwitchNode } from './nodes/SwitchNode';
import { CloudNode } from './nodes/CloudNode';
import { HostNode } from './nodes/HostNode';

export const nodeTypes = {
  router: RouterNode,
  switch: SwitchNode,
  cloud: CloudNode,
  host: HostNode,
};
