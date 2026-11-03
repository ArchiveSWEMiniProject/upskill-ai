// The student's skill gap as a ranked list (RM-3, REQ-F2-04): the most important
// skill first, each with the current level against the required level.
export type Level = "beginner" | "intermediate" | "advanced";

export type GapItem = {
  rank: number;
  skill_id: number;
  skill_name: string;
  required_level: Level;
  current_level: Level | null; // null: the student has no entry for the skill
  weight: number;
};

export type Gap = { role_id: number; role_name: string; items: GapItem[] };

const LEVEL_LABEL: Record<Level, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

export function GapList({ items }: { items: GapItem[] }) {
  return (
    <ol className="entries" aria-label="Skills to work on, most important first">
      {items.map((item) => (
        <li key={item.skill_id}>
          <strong>
            {item.rank}. {item.skill_name}
          </strong>
          <span>
            Current: {item.current_level ? LEVEL_LABEL[item.current_level] : "Not held yet"}
            {" - "}Required: {LEVEL_LABEL[item.required_level]}
          </span>
          <span className="muted">Importance to the role: {item.weight}</span>
        </li>
      ))}
    </ol>
  );
}
