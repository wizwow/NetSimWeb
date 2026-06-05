import { describe, expect, it } from 'vitest';

import { docReportFileName, exportFileName, pdfReportFileName, reportFileName, safeExportBaseName } from './exportFile';

describe('export file helpers', () => {
  it('creates a safe netsimflow filename from topology names', () => {
    expect(exportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.netsimflow.json');
    expect(exportFileName(' HQ / Branch? ')).toBe('HQ-Branch.netsimflow.json');
  });

  it('falls back to topology when the name has no usable characters', () => {
    expect(safeExportBaseName(' /// ')).toBe('topology');
    expect(exportFileName(undefined)).toBe('topology.netsimflow.json');
    expect(reportFileName(undefined)).toBe('topology.netsimflow.md');
    expect(pdfReportFileName(undefined)).toBe('topology.netsimflow.pdf');
    expect(docReportFileName(undefined)).toBe('topology.netsimflow.doc');
  });

  it('creates safe report filenames from topology names', () => {
    expect(reportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.netsimflow.md');
    expect(pdfReportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.netsimflow.pdf');
    expect(docReportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.netsimflow.doc');
  });
});
