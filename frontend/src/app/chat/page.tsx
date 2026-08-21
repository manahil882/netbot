import type { Metadata } from "next";
import { Suspense } from "react";
import AuthGuard from "@/components/AuthGuard";
import ChatScreen from "@/components/screens/ChatScreen";

export const metadata: Metadata = {
  title: "Workspace · NetBot",
};

export default function ChatPage() {
  return (
    <AuthGuard>
      <Suspense fallback={<div className="chat-loading">Loading workspace…</div>}>
        <ChatScreen />
      </Suspense>
    </AuthGuard>
  );
}
