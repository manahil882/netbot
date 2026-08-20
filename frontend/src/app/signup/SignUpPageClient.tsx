"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import SignUpScreen from "@/components/screens/SignUpScreen";
import EnrollScreen from "@/components/screens/EnrollScreen";
import { useAuth } from "@/lib/auth-context";

export default function SignUpPageClient() {
  const router = useRouter();
  const { ready, account, authed, login, markFaceEnrolled } = useAuth();
  const searchParams = useSearchParams();
  const faceOnly = searchParams.get("mode") === "face";

  useEffect(() => {
    if (!ready || !faceOnly) return;
    if (!account) router.replace("/signup");
  }, [ready, faceOnly, account, router]);

  function completeEnrollment() {
    markFaceEnrolled();
    login();
    router.replace("/chat");
  }

  if (!ready) return null;

  if (faceOnly) {
    if (!account) return null;

    return (
      <EnrollScreen
        autoStart
        onComplete={completeEnrollment}
      />
    );
  }

  return <SignUpScreen />;
}
