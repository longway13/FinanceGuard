import { Suspense } from "react"
import { DashboardSkeleton } from "@/components/dashboard-skeleton"
import { Dashboard } from "@/components/dashboard"

export default function DashboardPage({
  params,
}: {
  params: { fileId: string }
}) {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="container flex items-center h-16 px-4">
          <h1 className="text-xl font-bold">FinanceGuard</h1>
          <span className="ml-2 text-sm text-muted-foreground">Financial Product Risk Analysis</span>
        </div>
      </header>
      <main className="flex-1 container px-4 py-6">
        <Suspense fallback={<DashboardSkeleton />}>
          <Dashboard fileId={params.fileId} />
        </Suspense>
      </main>
    </div>
  )
}

