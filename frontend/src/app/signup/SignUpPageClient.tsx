"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import SignUpScreen from "@/components/screens/SignUpScreen";
import EnrollScreen from "@/components/screens/EnrollScreen";
import { apiFaceEnroll } from "@/lib/api/client";
import { useAuth } from "@/lib/auth-context";

export default function SignUpPageClient() {
  const router = useRouter();
  const { ready, account, markFaceEnrolled } = useAuth();
  const searchParams = useSearchParams();
  const faceOnly = searchParams.get("mode") === "face";

  useEffect(() => {
    if (!ready || !faceOnly) return;
    if (!account) router.replace("/signup");
  }, [ready, faceOnly, account, router]);

  async function completeEnrollment(faceImage: Blob | null) {
    if (!faceImage) {
      throw new Error("Could not capture your face. Keep the camera on and try again.");
    }
    await apiFaceEnroll(faceImage);
    markFaceEnrolled();
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
