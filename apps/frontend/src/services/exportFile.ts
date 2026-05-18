export const EXPORT_FILE_EXTENSION = '.netsimflow.json';
export const REPORT_FILE_EXTENSION = '.netsimflow.md';

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

export function downloadJsonFile(data: unknown, fileName: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  downloadBlob(blob, fileName);
}

export function downloadTextFile(text: string, fileName: string, type = 'text/plain'): void {
  downloadBlob(new Blob([text], { type }), fileName);
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
