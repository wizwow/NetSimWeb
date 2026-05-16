import type { NetworkNode } from '@netsimflow/shared-types';

interface BaseNodeProps {
  data: NetworkNode;
  icon: React.ReactNode;
  handles: React.ReactNode;
}

export const BaseNode: React.FC<BaseNodeProps> = ({ data, icon, handles }) => {
  const isSelected = false; // We can get this from props later if needed via useStore
  const status = data.runtimeState?.status || 'stopped';
  const role = data.role || data.baseType;

  return (
    <div className={`netsim-node ${isSelected ? 'selected' : ''}`}>
      <div className="netsim-node-icon">
        {icon}
      </div>
      <div className="netsim-node-content">
        <span className="netsim-node-label">{data.label}</span>
        <span className="netsim-node-sub">{role.toUpperCase()}</span>
      </div>
      
      <div className={`status-dot ${status}`} title={`Status: ${status}`}></div>
      
      {handles}
    </div>
  );
};
