import Link from 'next/link'

interface UpgradePromptProps {
  feature: string
  currentPlan: string
  className?: string
}

export function UpgradePrompt({ feature, currentPlan, className }: UpgradePromptProps) {
  return (
    <div className={`border rounded-lg p-4 bg-indigo-50 border-indigo-200 ${className ?? ''}`}>
      <p className="text-sm text-indigo-800">
        {feature} requires an upgrade. You&apos;re on the{' '}
        <strong className="capitalize">{currentPlan}</strong> plan.
      </p>
      <Link
        href="/dashboard/billing"
        className="text-indigo-600 font-medium text-sm hover:underline mt-1 inline-block"
      >
        View plans →
      </Link>
    </div>
  )
}
