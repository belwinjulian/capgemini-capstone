import { ChatInterface } from "@/components/chat/ChatInterface";

export default function Page() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-zinc-200 px-6 py-3 flex items-center justify-between bg-background">
        <h1 className="text-sm font-medium tracking-tight">
          Patient Safety Intelligence
        </h1>
        <span className="font-mono text-[11px] uppercase tracking-widest text-zinc-500">
          Capgemini
        </span>
      </header>
      <main className="flex-1">
        <ChatInterface />
      </main>
    </div>
  );
}
