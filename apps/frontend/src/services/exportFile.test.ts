import { describe, expect, it } from 'vitest';

import { exportFileName, safeExportBaseName } from './exportFile';

describe('export file helpers', () => {
  it('creates a safe netsimflow filename from topology names', () => {
    expect(exportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.netsimflow.json');
    expect(exportFileName(' HQ / Branch? ')).toBe('HQ-Branch.netsimflow.json');
  });

  it('falls back to topology when the name has no usable characters', () => {
    expect(safeExportBaseName(' /// ')).toBe('topology');
    expect(exportFileName(undefined)).toBe('topology.netsimflow.json');
  });
});
