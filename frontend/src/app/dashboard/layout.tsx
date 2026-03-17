// Dashboard layout — authenticated users only
// Contains sidebar navigation and top header
// Protected by middleware.ts — redirects unauthenticated users to /login

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen">
      {/* Sidebar will go here */}
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  )
}
