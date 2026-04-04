'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { Logo } from '@/components/ui/Logo'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Mail } from 'lucide-react'

export default function ConfirmEmailPage() {
  const router = useRouter()
  const [resending, setResending] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)
  const [resendError, setResendError] = useState<string | null>(null)

  const handleResend = async () => {
    setResending(true)
    setResendError(null)
    setResendSuccess(false)

    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user?.email) {
      setResendError('Could not determine your email address. Please sign up again.')
      setResending(false)
      return
    }

    const { error } = await supabase.auth.resend({
      type: 'signup',
      email: user.email,
    })

    if (error) {
      setResendError(error.message)
    } else {
      setResendSuccess(true)
    }
    setResending(false)
  }

  const handleSignOut = async () => {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/login')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-[400px]">
        <div className="text-center mb-8 flex justify-center">
          <Logo size="lg" />
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-xl text-slate-900">Verify your email</CardTitle>
            <CardDescription>
              You need to verify your email address before accessing your dashboard.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center gap-4 py-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
                <Mail className="h-6 w-6 text-indigo-600" />
              </div>
              <p className="text-sm text-slate-600 text-center leading-relaxed">
                We&apos;ve sent a confirmation link to your email. Click the link to activate your account.
              </p>

              {resendError && (
                <div className="w-full rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
                  {resendError}
                </div>
              )}

              {resendSuccess && (
                <div className="w-full rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-sm text-emerald-700">
                  Confirmation email resent! Check your inbox and spam folder.
                </div>
              )}

              <Button
                variant="outline"
                onClick={handleResend}
                disabled={resending || resendSuccess}
                className="w-full"
              >
                {resending ? 'Sending...' : resendSuccess ? 'Email Sent' : 'Resend Confirmation Email'}
              </Button>

              <button
                onClick={handleSignOut}
                className="text-sm text-slate-500 hover:text-slate-700 hover:underline"
              >
                Sign out
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
