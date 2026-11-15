export type ProgressRecord = {
  progress_id: number;
  resource_id: number;
  status: "enrolled" | "in-progress" | "completed";
  completion_percentage: number;
};
