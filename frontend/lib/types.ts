// Shapes of the M1 API responses the pages use.
export type Profile = {
  student_id: number;
  name: string;
  education_level: string | null;
  target_role_id: number | null;
  created_at: string;
};

export type Role = { role_id: number; role_name: string };

// The active target role with how the student stands against it (UP-13).
export type TargetRole = {
  role_id: number;
  role_name: string;
  set_at: string | null;
  required: number;
  held: number;
  gap: number;
};
