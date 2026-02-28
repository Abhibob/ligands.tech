// Parse PAE JSON into a 2D number matrix for heatmap rendering
export function parsePaeJson(jsonText: string): number[][] | null {
  try {
    const data = JSON.parse(jsonText);

    // AlphaFold format: [{ predicted_aligned_error: number[][] }]
    if (Array.isArray(data) && data[0]?.predicted_aligned_error) {
      return data[0].predicted_aligned_error;
    }
    // Direct matrix format
    if (data.predicted_aligned_error) {
      return data.predicted_aligned_error;
    }
    // Flat matrix — try to reshape if it looks like one
    if (Array.isArray(data) && Array.isArray(data[0]) && typeof data[0][0] === 'number') {
      return data;
    }

    return null;
  } catch {
    return null;
  }
}
