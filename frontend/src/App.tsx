import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatView } from "@/components/ChatView";
import { CreateKbDialog } from "@/components/CreateKbDialog";
import { UploadDialog } from "@/components/UploadDialog";
import { KbManagerDialog } from "@/components/KbManagerDialog";
import { useAppStore } from "@/store/appStore";

export default function App() {
  const { activeKb } = useAppStore();
  const [createOpen, setCreateOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);

  return (
    <div className="flex h-full w-full overflow-hidden">
      <Sidebar
        onCreateKb={() => setCreateOpen(true)}
        onUpload={() => setUploadOpen(true)}
        onManageKb={() => setManageOpen(true)}
      />
      <main className="flex flex-1 flex-col overflow-hidden">
        <ChatView />
      </main>

      <CreateKbDialog open={createOpen} onOpenChange={setCreateOpen} />
      {activeKb && (
        <>
          <UploadDialog open={uploadOpen} onOpenChange={setUploadOpen} kbName={activeKb} />
          <KbManagerDialog open={manageOpen} onOpenChange={setManageOpen} kbName={activeKb} />
        </>
      )}
    </div>
  );
}
