export type NodeBaseType = 'router' | 'switch' | 'firewall' | 'cloud' | 'host' | 'site';
export type NodeStatus = 'stopped' | 'booting' | 'running' | 'error' | 'degraded';
export type VendorType = 'cisco' | 'juniper' | 'arista' | 'mikrotik' | 'generic';
export type Protocol = 'ospf' | 'bgp' | 'eigrp' | 'static' | 'rip';
export interface LogicalInterface {
    name: string;
    ip?: string;
    subnet?: string;
    mac?: string;
    status: 'up' | 'down';
}
export interface RoutingConfig {
    processId?: number;
    area?: number;
    routerId?: string;
    [key: string]: unknown;
}
export interface NetworkNode {
    id: string;
    label: string;
    position: {
        x: number;
        y: number;
    };
    baseType: NodeBaseType;
    role?: 'core' | 'distribution' | 'access' | 'edge' | 'hub' | 'spoke';
    protocols?: Protocol[];
    logicalConfig?: {
        interfaces: LogicalInterface[];
        routingConfig?: RoutingConfig;
        loopback?: string;
    };
    vendorSpec?: {
        vendor: VendorType;
        platform: string;
        imageRef?: string;
        cliConfig?: string;
        features?: Record<string, unknown>;
    };
    runtimeState?: {
        status: NodeStatus;
        cpuPercent?: number;
        memMB?: number;
        nodeId?: string;
    };
    tags: string[];
}
export interface NetworkLink {
    id: string;
    sourceNodeId: string;
    sourcePort: string;
    targetNodeId: string;
    targetPort: string;
    linkType: 'ethernet' | 'serial' | 'fiber' | 'vpn-tunnel' | 'logical';
    ipConfig?: {
        subnet: string;
        sourceIp?: string;
        targetIp?: string;
    };
    qos?: {
        bandwidthMbps?: number;
        latencyMs?: number;
        packetLossPercent?: number;
    };
    faultState?: {
        active: boolean;
        type?: 'link-down' | 'high-latency' | 'packet-loss';
        triggeredAt?: string;
    };
}
export interface Topology {
    id: string;
    ownerId?: string;
    name: string;
    description?: string;
    abstractionLevel: 'logical' | 'vendor-specific';
    engineTopoId?: string;
    status: 'draft' | 'running' | 'stopped' | 'error';
    nodes: NetworkNode[];
    edges: NetworkLink[];
    createdAt?: string;
    updatedAt?: string;
}
