// Shapes of the M1 API responses the pages use.
export type Profile = {
  student_id: number;
  name: string;
  education_level: string | null;
  target_role_id: number | null;
  created_at: string;
};
