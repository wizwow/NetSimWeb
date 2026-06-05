import { describe, expect, it } from 'vitest';

import { docReportFileName, exportFileName, pdfReportFileName, reportFileName, safeExportBaseName } from './exportFile';

describe('export file helpers', () => {
  it('creates a safe octet filename from topology names', () => {
    expect(exportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.octet.json');
    expect(exportFileName(' HQ / Branch? ')).toBe('HQ-Branch.octet.json');
  });

  it('falls back to topology when the name has no usable characters', () => {
    expect(safeExportBaseName(' /// ')).toBe('topology');
    expect(exportFileName(undefined)).toBe('topology.octet.json');
    expect(reportFileName(undefined)).toBe('topology.octet.md');
    expect(pdfReportFileName(undefined)).toBe('topology.octet.pdf');
    expect(docReportFileName(undefined)).toBe('topology.octet.doc');
  });

  it('creates safe report filenames from topology names', () => {
    expect(reportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.octet.md');
    expect(pdfReportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.octet.pdf');
    expect(docReportFileName('OSPF 3 Sites')).toBe('OSPF-3-Sites.octet.doc');
  });
});
