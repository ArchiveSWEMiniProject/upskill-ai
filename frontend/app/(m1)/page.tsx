"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getToken } from "@/lib/api";

import { LoginForm, RegisterForm } from "./_components/AuthForms";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    if (getToken()) router.replace("/profile");
  }, [router]);

  return (
    <>
      <header>
        <h1>UpSkill-AI</h1>
      </header>
      <main className="split">
        <section>
          <h2>Log in</h2>
          <LoginForm />
        </section>
        <section>
          <h2>Create a student account</h2>
          <RegisterForm />
        </section>
      </main>
    </>
  );
}
