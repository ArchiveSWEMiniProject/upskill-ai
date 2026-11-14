// The student's skill gap as a ranked list (RM-3, REQ-F2-04): the most important
// skill first, each with the current level against the required level.
export type Level = "beginner" | "intermediate" | "advanced";

export type ResourceType = "course" | "certification" | "project_idea";

export type Resource = {
  item_id: number;
  title: string;
  item_type: ResourceType;
  coverage_level: Level; // the level this resource brings the skill to
  duration: string | null;
  source: string | null;
  source_url: string;
};

export type GapItem = {
  rank: number;
  skill_id: number;
  skill_name: string;
  required_level: Level;
  current_level: Level | null; // null: the student has no entry for the skill
  weight: number;
  resources: Resource[]; // ranked approved catalogue resources; empty if none suit
};

export type Gap = { role_id: number; role_name: string; items: GapItem[] };

const LEVEL_LABEL: Record<Level, string> = {
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

const TYPE_LABEL: Record<ResourceType, string> = {
  course: "Course",
  certification: "Certification",
  project_idea: "Project idea",
};

function resourceDetails(resource: Resource): string {
  return [
    TYPE_LABEL[resource.item_type] ?? resource.item_type,
    LEVEL_LABEL[resource.coverage_level],
    resource.duration,
    resource.source,
  ]
    .filter(Boolean)
    .join(" - ");
}

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
          <div role="group" aria-label={`Resources for ${item.skill_name}`}>
            {item.resources.length === 0 ? (
              <span className="muted">No catalogue resources for this skill yet.</span>
            ) : (
              item.resources.map((resource) => (
                <div key={resource.item_id}>
                  <a href={resource.source_url} target="_blank" rel="noopener noreferrer">
                    {resource.title}
                  </a>{" "}
                  <span className="muted">{resourceDetails(resource)}</span>
                </div>
              ))
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}
