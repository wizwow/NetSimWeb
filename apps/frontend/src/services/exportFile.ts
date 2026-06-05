export const EXPORT_FILE_EXTENSION = '.octet.json';
export const REPORT_FILE_EXTENSION = '.octet.md';
export const PDF_REPORT_FILE_EXTENSION = '.octet.pdf';
export const DOC_REPORT_FILE_EXTENSION = '.octet.doc';

export function safeExportBaseName(name: string | undefined): string {
  const cleaned = (name || 'topology')
    .trim()
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  return cleaned || 'topology';
}

export function exportFileName(name: string | undefined): string {
  return `${safeExportBaseName(name)}${EXPORT_FILE_EXTENSION}`;
}

export function reportFileName(name: string | undefined): string {
  return `${safeExportBaseName(name)}${REPORT_FILE_EXTENSION}`;
}

export function pdfReportFileName(name: string | undefined): string {
  return `${safeExportBaseName(name)}${PDF_REPORT_FILE_EXTENSION}`;
}

export function docReportFileName(name: string | undefined): string {
  return `${safeExportBaseName(name)}${DOC_REPORT_FILE_EXTENSION}`;
}

export function downloadJsonFile(data: unknown, fileName: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  downloadBlob(blob, fileName);
}

export function downloadTextFile(text: string, fileName: string, type = 'text/plain'): void {
  downloadBlob(new Blob([text], { type }), fileName);
}

export function downloadBinaryFile(data: BlobPart, fileName: string, type: string): void {
  downloadBlob(new Blob([data], { type }), fileName);
}

function downloadBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
