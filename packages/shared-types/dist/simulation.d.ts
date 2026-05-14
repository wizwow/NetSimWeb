import { NodeStatus } from './topology';
export type FaultType = 'link-down' | 'high-latency' | 'packet-loss';
export type ProbeType = 'ping' | 'traceroute';
export interface ProbeResult {
    success: boolean;
    output: string;
    rttMs?: number;
    hops?: Array<{
        ip: string;
        rttMs: number;
    }>;
}
export interface FaultRequest {
    linkId: string;
    faultType: FaultType;
}
export type SimulationEvent = {
    type: 'NODE_STATUS_CHANGED';
    nodeId: string;
    status: NodeStatus;
} | {
    type: 'LINK_FAULT_INJECTED';
    linkId: string;
    faultType: FaultType;
} | {
    type: 'OSPF_ADJACENCY_CHANGED';
    nodeId: string;
    neighborId: string;
    state: string;
} | {
    type: 'PROBE_RESULT';
    probeId: string;
    result: ProbeResult;
} | {
    type: 'LINK_DOWN';
    linkId: string;
    timestamp: string;
};
