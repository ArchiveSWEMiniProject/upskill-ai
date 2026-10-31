// Counts characters the way the API does (Python's len counts code points, not
// UTF-16 units), so the live count matches the API's "is N characters" error.
export function countCharacters(text: string): number {
  return [...text].length;
}

export function counterLabel(count: number, max: number): string {
  const label = `${count} / ${max} characters`;
  return count > max ? `${label}, ${count - max} over the limit` : label;
}
