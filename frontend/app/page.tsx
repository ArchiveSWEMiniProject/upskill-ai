import M3Progress from "@/components/M3Progress";

export default function Home() {
  return <main className="shell">
    <header><p className="eyebrow">UpSkill-AI · M3</p><h1>Progress tracker</h1>
      <p>Track your learning, submit completion evidence and review milestones.</p></header>
    <M3Progress />
  </main>;
}
