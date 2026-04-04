'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'
import { Logo } from '@/components/ui/Logo'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CheckCircle, AlertTriangle, Loader2 } from 'lucide-react'

type PageState = 'loading' | 'form' | 'success' | 'expired'

export default function ResetPasswordPage() {
  const router = useRouter()
  const [state, setState] = useState<PageState>('loading')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [updating, setUpdating] = useState(false)

  useEffect(() => {
    const supabase = createClient()

    // Check if the user has a valid session (set by the auth callback code exchange)
    const checkSession = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        setState('form')
      } else {
        // Wait briefly for any pending session establishment
        setTimeout(async () => {
          const { data: { session: retrySession } } = await supabase.auth.getSession()
          setState(retrySession ? 'form' : 'expired')
        }, 2000)
      }
    }

    checkSession()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setUpdating(true)
    const supabase = createClient()
    const { error: updateError } = await supabase.auth.updateUser({ password })

    if (updateError) {
      setError(updateError.message)
      setUpdating(false)
      return
    }

    setState('success')
    setTimeout(() => {
      router.push('/dashboard')
    }, 2000)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-[400px]">
        <div className="text-center mb-8 flex justify-center">
          <Logo size="lg" />
        </div>

        <Card>
          {state === 'loading' && (
            <>
              <CardHeader>
                <CardTitle className="text-xl text-slate-900">Verifying link...</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center gap-4 py-8">
                  <Loader2 className="h-8 w-8 text-indigo-600 animate-spin" />
                  <p className="text-sm text-slate-500">Please wait while we verify your reset link.</p>
                </div>
              </CardContent>
            </>
          )}

          {state === 'expired' && (
            <>
              <CardHeader>
                <CardTitle className="text-xl text-slate-900">Invalid or expired link</CardTitle>
                <CardDescription>This password reset link is invalid or has expired.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center gap-4 py-4">
                  <AlertTriangle className="h-10 w-10 text-amber-500" />
                  <p className="text-sm text-slate-500 text-center">
                    Password reset links expire after 1 hour. Please request a new one.
                  </p>
                  <Link
                    href="/forgot-password"
                    className="inline-flex items-center rounded-lg bg-indigo-700 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-800 transition-colors"
                  >
                    Request a new link
                  </Link>
                </div>
              </CardContent>
            </>
          )}

          {state === 'success' && (
            <>
              <CardHeader>
                <CardTitle className="text-xl text-slate-900">Password updated</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center gap-4 py-4">
                  <CheckCircle className="h-10 w-10 text-emerald-500" />
                  <p className="text-sm text-slate-700 font-medium">
                    Password updated successfully!
                  </p>
                  <p className="text-sm text-slate-500">Redirecting to dashboard...</p>
                </div>
              </CardContent>
            </>
          )}

          {state === 'form' && (
            <>
              <CardHeader>
                <CardTitle className="text-xl text-slate-900">Set new password</CardTitle>
                <CardDescription>Choose a new password for your account.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {error && (
                    <div className="rounded-lg bg-rose-50 border border-rose-200 p-3 text-sm text-rose-700">
                      {error}
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <Label htmlFor="password">New password</Label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="Min. 8 characters"
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                    />
                    <p className="text-xs text-slate-400">Password must be at least 8 characters.</p>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="confirm-password">Confirm password</Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      placeholder="Repeat your new password"
                      autoComplete="new-password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                  </div>

                  <Button
                    type="submit"
                    className="w-full bg-indigo-700 hover:bg-indigo-800 text-white"
                    disabled={updating || password.length < 8 || password !== confirmPassword}
                  >
                    {updating ? 'Updating...' : 'Update Password'}
                  </Button>
                </form>
              </CardContent>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
